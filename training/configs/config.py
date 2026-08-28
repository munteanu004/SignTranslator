"""
Configurare centralizata pentru antrenare SignTranslator.
"""
from dataclasses import dataclass, field
from typing import List, Optional
    

@dataclass
class DataConfig:
    # Cai catre date
    how2sign_pkl_dir: str = "how2sign_pkls_default_shape/how2sign_pkls_cropTrue_shapeFalse"
    ro_dataset_json: str = "ro-sign-language-recognition/datasets/processed_dataset/dataset.json"
    ro_videos_dir: str = "ro-sign-language-recognition/datasets/processed_dataset/videos"

    # Procesare
    max_seq_len: int = 150          # Frame-uri maxime per secventa
    num_joints: int = 75            # 33 pose + 21 left hand + 21 right hand
    joint_dim: int = 3              # x, y, confidence/z
    max_pkls: Optional[int] = None  # None = toate, sau un numar pentru test rapid
    num_workers: int = 4


@dataclass
class GraphConfig:
    # Definire graf schelet uman (conexiuni intre articulatii)
    # MediaPipe Pose (33) + Left Hand (21) + Right Hand (21) = 75 joints
    num_joints: int = 75
    spatial_kernel_size: int = 3
    temporal_kernel_size: int = 9
    num_scales: int = 4


@dataclass
class ModelConfig:
    # Arhitectura
    in_channels: int = 3            # x, y, confidence
    num_joints: int = 75
    hidden_dim: int = 256
    num_classes: int = 1926         # Numarul de glosuri romanesti

    # Graph Convolution
    gcn_layers: int = 4
    gcn_dropout: float = 0.1

    # Transformer
    transformer_heads: int = 8
    transformer_layers: int = 4
    transformer_dim: int = 256
    transformer_dropout: float = 0.1
    transformer_ff_dim: int = 1024

    # Temporal Convolution
    tcn_channels: List[int] = field(default_factory=lambda: [64, 128, 256])
    tcn_kernel_size: int = 3


@dataclass
class TrainConfig:
    # Pre-antrenare
    pretrain_epochs: int = 50
    pretrain_lr: float = 1e-3
    pretrain_batch_size: int = 32
    pretrain_warmup_epochs: int = 5

    # Fine-tuning
    finetune_epochs: int = 80
    finetune_lr: float = 1e-4
    finetune_batch_size: int = 16
    finetune_warmup_epochs: int = 3

    # Comun
    weight_decay: float = 1e-4
    grad_clip: float = 1.0
    label_smoothing: float = 0.1
    mixup_alpha: float = 0.2

    # Scheduler
    scheduler: str = "cosine"  # "cosine" sau "plateau"
    min_lr: float = 1e-7

    # Salvare
    save_dir: str = "models"
    save_every: int = 5
    patience: int = 15  # Early stopping


@dataclass
class Config:
    data: DataConfig = field(default_factory=DataConfig)
    graph: GraphConfig = field(default_factory=GraphConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    train: TrainConfig = field(default_factory=TrainConfig)
    seed: int = 42
    device: str = "cuda"  # "cuda" sau "cpu"
