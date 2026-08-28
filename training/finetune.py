"""
Fine-tuning SignTranslator pe date romanesti.

Incarca modelul pre-antrenat pe How2Sign si il antreneaza
pe clasificare de glosuri romanesti.

Tehnici folosite:
  - Label smoothing — previne overfitting pe clase
  - Mixup augmentation — interpoleaza intre sample-uri
  - Cosine annealing — scadere graduala a learning rate-ului
  - Early stopping — opreste daca nu mai invata
  - Gradient accumulation — simuleaza batch-uri mai mari
"""
import math
import os
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, random_split
from tqdm import tqdm

from model import create_model
from dataset import RomanianSignDataset
from configs import Config


def mixup_data(x: torch.Tensor, y: torch.Tensor, alpha: float = 0.2):
    """
    Mixup augmentation: interpoleaza intre perechi de sample-uri.
    Ajuta la generalizare si previne overfitting.
    """
    if alpha <= 0:
        return x, y, y, 1.0

    lam = np.random.beta(alpha, alpha)
    lam = max(lam, 1 - lam)  # Asigura lam >= 0.5

    B = x.shape[0]
    index = torch.randperm(B, device=x.device)

    mixed_x = lam * x + (1 - lam) * x[index]
    y_a, y_b = y, y[index]

    return mixed_x, y_a, y_b, lam


def mixup_criterion(criterion, pred, y_a, y_b, lam):
    """Loss pentru mixup."""
    return lam * criterion(pred, y_a) + (1 - lam) * criterion(pred, y_b)


def finetune(cfg: Config, pretrained_path: str = None):
    """Ruleaza fine-tuning pe date romanesti."""
    device = torch.device(cfg.device if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")

    # Dataset romanesc
    train_dataset = RomanianSignDataset(
        dataset_json=cfg.data.ro_dataset_json,
        videos_dir=cfg.data.ro_videos_dir,
        max_seq_len=cfg.data.max_seq_len,
        num_joints=cfg.data.num_joints,
        split='train',
        augment=True,
        cache_dir='data/ro_cache'
    )

    test_dataset = RomanianSignDataset(
        dataset_json=cfg.data.ro_dataset_json,
        videos_dir=cfg.data.ro_videos_dir,
        max_seq_len=cfg.data.max_seq_len,
        num_joints=cfg.data.num_joints,
        split='test',
        augment=False,
        cache_dir='data/ro_cache'
    )

    # Actualizeaza numarul de clase
    cfg.model.num_classes = train_dataset.num_classes
    print(f"Clase (glosuri): {cfg.model.num_classes}")

    # Split train -> train + val
    N = len(train_dataset)
    val_n = max(1, int(N * 0.1))
    train_n = N - val_n
    train_set, val_set = random_split(
        train_dataset, [train_n, val_n],
        generator=torch.Generator().manual_seed(cfg.seed)
    )

    train_loader = DataLoader(
        train_set, batch_size=cfg.train.finetune_batch_size,
        shuffle=True, num_workers=cfg.data.num_workers, pin_memory=True, drop_last=True
    )
    val_loader = DataLoader(
        val_set, batch_size=cfg.train.finetune_batch_size,
        shuffle=False, num_workers=cfg.data.num_workers, pin_memory=True
    )
    test_loader = DataLoader(
        test_dataset, batch_size=cfg.train.finetune_batch_size,
        shuffle=False, num_workers=cfg.data.num_workers, pin_memory=True
    )

    # Model
    model = create_model(cfg).to(device)

    # Incarca greutati pre-antrenate
    if pretrained_path and os.path.exists(pretrained_path):
        checkpoint = torch.load(pretrained_path, map_location=device)
        # Incarca doar backbone-ul (fara classifier)
        state_dict = checkpoint['backbone']
        # Filtreaza cheile classifier-ului
        model_dict = model.state_dict()
        pretrained_dict = {k: v for k, v in state_dict.items()
                          if k in model_dict and model_dict[k].shape == v.shape}
        model_dict.update(pretrained_dict)
        model.load_state_dict(model_dict, strict=False)
        loaded = len(pretrained_dict)
        total = len(model_dict)
        print(f"Incarcat {loaded}/{total} parametri din {pretrained_path}")
        print(f"Pre-train val_loss: {checkpoint.get('val_loss', 'N/A')}")
    else:
        print("ATENTIE: Antrenare de la zero (fara pre-antrenare)!")

    num_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Model parametri: {num_params:,}")

    # Loss cu label smoothing
    criterion = nn.CrossEntropyLoss(label_smoothing=cfg.train.label_smoothing)

    # Optimizer — learning rate diferentiat
    # Backbone (pre-antrenat) primeste LR mai mic
    # Classifier (nou) primeste LR mai mare
    backbone_params = []
    classifier_params = []
    for name, param in model.named_parameters():
        if 'classifier' in name:
            classifier_params.append(param)
        else:
            backbone_params.append(param)

    optimizer = torch.optim.AdamW([
        {'params': backbone_params, 'lr': cfg.train.finetune_lr},
        {'params': classifier_params, 'lr': cfg.train.finetune_lr * 10},  # 10x mai mare
    ], weight_decay=cfg.train.weight_decay)

    # Cosine annealing scheduler
    total_steps = cfg.train.finetune_epochs * len(train_loader)
    warmup_steps = cfg.train.finetune_warmup_epochs * len(train_loader)

    def lr_lambda(step):
        if step < warmup_steps:
            return step / max(1, warmup_steps)
        progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
        return max(cfg.train.min_lr / cfg.train.finetune_lr,
                   0.5 * (1.0 + math.cos(math.pi * progress)))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    # Training
    os.makedirs(cfg.train.save_dir, exist_ok=True)
    best_val_acc = 0.0
    best_val_loss = float('inf')
    patience_counter = 0
    step = 0

    # Salvare gloss mapping
    gloss_mapping = {
        'glosses': train_dataset.glosses,
        'gloss_to_idx': train_dataset.gloss_to_idx,
        'num_classes': train_dataset.num_classes
    }
    import json
    with open(os.path.join(cfg.train.save_dir, 'gloss_mapping.json'), 'w', encoding='utf-8') as f:
        json.dump(gloss_mapping, f, ensure_ascii=False, indent=2)

    for epoch in range(1, cfg.train.finetune_epochs + 1):
        model.train()
        epoch_loss = 0.0
        correct = 0
        total = 0

        pbar = tqdm(train_loader, desc=f'FT Ep {epoch}/{cfg.train.finetune_epochs}')
        for batch in pbar:
            joints = batch['joints'].to(device)
            mask = batch['mask'].to(device)
            labels = batch['label'].to(device)

            # Mixup augmentation
            if cfg.train.mixup_alpha > 0:
                joints, labels_a, labels_b, lam = mixup_data(
                    joints, labels, cfg.train.mixup_alpha
                )
            else:
                labels_a, labels_b, lam = labels, labels, 1.0

            logits = model(joints, mask=mask)

            if cfg.train.mixup_alpha > 0:
                loss = mixup_criterion(criterion, logits, labels_a, labels_b, lam)
            else:
                loss = criterion(logits, labels)

            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), cfg.train.grad_clip)
            optimizer.step()
            scheduler.step()
            step += 1

            epoch_loss += loss.item()
            _, predicted = logits.max(1)
            total += labels.shape[0]
            correct += predicted.eq(labels_a).sum().item()

            pbar.set_postfix(
                loss=f'{loss.item():.4f}',
                acc=f'{100.0 * correct / total:.1f}%',
                lr=f'{scheduler.get_last_lr()[0]:.2e}'
            )

        epoch_loss /= len(train_loader)
        train_acc = 100.0 * correct / total

        # Validare
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        top5_correct = 0

        with torch.no_grad():
            for batch in val_loader:
                joints = batch['joints'].to(device)
                mask = batch['mask'].to(device)
                labels = batch['label'].to(device)

                logits = model(joints, mask=mask)
                loss = criterion(logits, labels)

                val_loss += loss.item()
                _, predicted = logits.max(1)
                val_total += labels.shape[0]
                val_correct += predicted.eq(labels).sum().item()

                # Top-5 accuracy
                _, top5_pred = logits.topk(5, dim=1)
                top5_correct += sum(labels[i] in top5_pred[i] for i in range(labels.shape[0]))

        val_loss /= max(len(val_loader), 1)
        val_acc = 100.0 * val_correct / max(val_total, 1)
        val_top5 = 100.0 * top5_correct / max(val_total, 1)

        marker = ''
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_val_loss = val_loss
            patience_counter = 0
            save_path = os.path.join(cfg.train.save_dir, 'finetuned_best.pth')
            torch.save({
                'model': model.state_dict(),
                'epoch': epoch,
                'val_acc': best_val_acc,
                'val_loss': best_val_loss,
                'num_classes': cfg.model.num_classes,
                'config': cfg,
            }, save_path)
            marker = f' << BEST (salvat)'
        else:
            patience_counter += 1

        print(f'Ep {epoch:3d} | Train Loss: {epoch_loss:.4f} Acc: {train_acc:.1f}% '
              f'| Val Loss: {val_loss:.4f} Acc: {val_acc:.1f}% Top5: {val_top5:.1f}%{marker}')

        # Early stopping
        if patience_counter >= cfg.train.patience:
            print(f'\nEarly stopping la epoca {epoch} (patience={cfg.train.patience})')
            break

        # Salvare periodica
        if epoch % cfg.train.save_every == 0:
            save_path = os.path.join(cfg.train.save_dir, f'finetuned_ep{epoch}.pth')
            torch.save({
                'model': model.state_dict(),
                'epoch': epoch,
                'val_acc': val_acc,
            }, save_path)

    # === TEST FINAL ===
    print('\n=== Evaluare pe setul de test ===')
    best_ckpt = torch.load(os.path.join(cfg.train.save_dir, 'finetuned_best.pth'),
                           map_location=device)
    model.load_state_dict(best_ckpt['model'])
    model.eval()

    test_correct = 0
    test_total = 0
    test_top5 = 0

    with torch.no_grad():
        for batch in tqdm(test_loader, desc='Test'):
            joints = batch['joints'].to(device)
            mask = batch['mask'].to(device)
            labels = batch['label'].to(device)

            logits = model(joints, mask=mask)
            _, predicted = logits.max(1)
            test_total += labels.shape[0]
            test_correct += predicted.eq(labels).sum().item()

            _, top5_pred = logits.topk(min(5, logits.shape[1]), dim=1)
            test_top5 += sum(labels[i] in top5_pred[i] for i in range(labels.shape[0]))

    test_acc = 100.0 * test_correct / max(test_total, 1)
    test_top5_acc = 100.0 * test_top5 / max(test_total, 1)
    print(f'Test Accuracy:     {test_acc:.2f}%')
    print(f'Test Top-5 Acc:    {test_top5_acc:.2f}%')
    print(f'Best Val Accuracy: {best_val_acc:.2f}%')

    return os.path.join(cfg.train.save_dir, 'finetuned_best.pth')


if __name__ == '__main__':
    cfg = Config()
    pretrained = os.path.join(cfg.train.save_dir, 'pretrained_best.pth')
    finetune(cfg, pretrained_path=pretrained)
