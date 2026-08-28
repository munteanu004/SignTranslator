#!/usr/bin/env python3
"""
SignTranslator — Script principal de antrenare.

Utilizare:
  # Pasul 0: Pre-proceseaza videourile romanesti (o singura data)
  python train.py --stage cache

  # Pasul 1: Pre-antrenare pe How2Sign
  python train.py --stage pretrain

  # Pasul 2: Fine-tuning pe date romanesti
  python train.py --stage finetune

  # Sau totul dintr-o singura comanda:
  python train.py --stage all

  # Test rapid (putine date, verificare ca merge):
  python train.py --stage pretrain --max_pkls 100 --epochs 2 --batch_size 8
"""
import argparse
import os
import sys
import torch

# Adauga directorul curent in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from configs import Config
from pretrain import pretrain
from finetune import finetune
from dataset import cache_all_videos


def parse_args():
    p = argparse.ArgumentParser(description='SignTranslator Training')

    p.add_argument('--stage', type=str, required=True,
                   choices=['cache', 'pretrain', 'finetune', 'all'],
                   help='Etapa: cache, pretrain, finetune, sau all')

    # Override-uri pentru configurare
    p.add_argument('--device', type=str, default=None, help='cuda sau cpu')
    p.add_argument('--epochs', type=int, default=None, help='Numar de epoci')
    p.add_argument('--batch_size', type=int, default=None, help='Batch size')
    p.add_argument('--lr', type=float, default=None, help='Learning rate')
    p.add_argument('--max_pkls', type=int, default=None, help='Limita pkl-uri How2Sign')
    p.add_argument('--num_workers', type=int, default=None, help='Numar workers DataLoader')
    p.add_argument('--hidden_dim', type=int, default=None, help='Dimensiune hidden')
    p.add_argument('--pretrained_path', type=str, default=None, help='Cale model pre-antrenat')
    p.add_argument('--save_dir', type=str, default=None, help='Director salvare modele')

    # Cai date
    p.add_argument('--how2sign_dir', type=str, default=None, help='Director pkl-uri How2Sign')
    p.add_argument('--ro_json', type=str, default=None, help='Cale dataset.json romanesc')
    p.add_argument('--ro_videos', type=str, default=None, help='Director videouri romanesti')
    p.add_argument('--cache_dir', type=str, default='data/ro_cache', help='Director cache keypoints')

    return p.parse_args()


def apply_overrides(cfg: Config, args):
    """Aplica override-urile din linia de comanda."""
    if args.device:
        cfg.device = args.device
    if args.max_pkls:
        cfg.data.max_pkls = args.max_pkls
    if args.num_workers is not None:
        cfg.data.num_workers = args.num_workers
    if args.hidden_dim:
        cfg.model.hidden_dim = args.hidden_dim
        cfg.model.transformer_dim = args.hidden_dim
    if args.save_dir:
        cfg.train.save_dir = args.save_dir
    if args.how2sign_dir:
        cfg.data.how2sign_pkl_dir = args.how2sign_dir
    if args.ro_json:
        cfg.data.ro_dataset_json = args.ro_json
    if args.ro_videos:
        cfg.data.ro_videos_dir = args.ro_videos

    # Override-uri specifice stagiului
    if args.stage in ('pretrain', 'all'):
        if args.epochs:
            cfg.train.pretrain_epochs = args.epochs
        if args.batch_size:
            cfg.train.pretrain_batch_size = args.batch_size
        if args.lr:
            cfg.train.pretrain_lr = args.lr

    if args.stage in ('finetune', 'all'):
        if args.epochs:
            cfg.train.finetune_epochs = args.epochs
        if args.batch_size:
            cfg.train.finetune_batch_size = args.batch_size
        if args.lr:
            cfg.train.finetune_lr = args.lr

    return cfg


def main():
    args = parse_args()
    cfg = Config()
    cfg = apply_overrides(cfg, args)

    # Info sistem
    print("=" * 60)
    print("  SignTranslator — Antrenare Model")
    print("=" * 60)
    print(f"  Stage: {args.stage}")
    print(f"  Device: {cfg.device}")
    if torch.cuda.is_available():
        print(f"  GPU: {torch.cuda.get_device_name(0)}")
        mem = torch.cuda.get_device_properties(0).total_mem / 1e9
        print(f"  Memorie GPU: {mem:.1f} GB")
    else:
        print("  GPU: Nu este disponibil (se foloseste CPU)")
    print(f"  PyTorch: {torch.__version__}")
    print("=" * 60)

    if args.stage == 'cache':
        print("\n>>> Pasul 0: Pre-procesare videouri romanesti")
        cache_all_videos(
            cfg.data.ro_dataset_json,
            cfg.data.ro_videos_dir,
            args.cache_dir
        )

    elif args.stage == 'pretrain':
        print("\n>>> Pasul 1: Pre-antrenare pe How2Sign")
        pretrain(cfg)

    elif args.stage == 'finetune':
        print("\n>>> Pasul 2: Fine-tuning pe date romanesti")
        pretrained = args.pretrained_path or os.path.join(cfg.train.save_dir, 'pretrained_best.pth')
        finetune(cfg, pretrained_path=pretrained)

    elif args.stage == 'all':
        print("\n>>> Pasul 0: Pre-procesare videouri romanesti")
        cache_all_videos(
            cfg.data.ro_dataset_json,
            cfg.data.ro_videos_dir,
            args.cache_dir
        )

        print("\n>>> Pasul 1: Pre-antrenare pe How2Sign")
        pretrained_path = pretrain(cfg)

        print("\n>>> Pasul 2: Fine-tuning pe date romanesti")
        finetune(cfg, pretrained_path=pretrained_path)

    print("\n>>> GATA!")


if __name__ == '__main__':
    main()
