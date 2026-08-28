"""
SignTranslator Model — Spatial-Temporal Graph Convolutional Network + Transformer

Arhitectura:
  1. Graph Convolution (GCN) — intelege relatiile spatiale intre articulatii
  2. Temporal Convolution (TCN) — capteaza miscarea in timp
  3. Transformer Encoder — atentie globala pe secventa temporala
  4. Classification Head — prezice gloss-ul (cuvantul din limbajul semnelor)

Aceasta arhitectura este inspirata din:
  - ST-GCN (Yan et al., 2018) pentru modelarea spatio-temporala a scheletului
  - Sign Language Transformers (Camgoz et al., 2020) pentru atentie temporala
"""
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional


# =============================================================================
# 1. GRAPH CONVOLUTION — modeleaza structura scheletului
# =============================================================================

def build_skeleton_adjacency(num_joints: int = 75) -> torch.Tensor:
    """
    Construieste matricea de adiacenta pentru scheletul uman.
    MediaPipe: 33 pose + 21 left hand + 21 right hand = 75 joints.
    """
    edges = []

    # === MediaPipe Pose (0-32) ===
    pose_edges = [
        (0, 1), (0, 4), (1, 2), (2, 3), (3, 7),   # Fata stanga
        (4, 5), (5, 6), (6, 8),                     # Fata dreapta
        (9, 10),                                     # Gura
        (11, 12),                                    # Umeri
        (11, 13), (13, 15), (15, 17), (15, 19), (15, 21),  # Brat stang
        (12, 14), (14, 16), (16, 18), (16, 20), (16, 22),  # Brat drept
        (11, 23), (12, 24),                          # Trunchi -> solduri
        (23, 24),                                    # Solduri
        (23, 25), (25, 27), (27, 29), (27, 31),     # Picior stang
        (24, 26), (26, 28), (28, 30), (28, 32),     # Picior drept
    ]
    edges.extend(pose_edges)

    # === Left Hand (33-53) — offset 33 ===
    hand_base = [
        (0, 1), (1, 2), (2, 3), (3, 4),       # Deget mare
        (0, 5), (5, 6), (6, 7), (7, 8),       # Index
        (0, 9), (9, 10), (10, 11), (11, 12),  # Mijlociu
        (0, 13), (13, 14), (14, 15), (15, 16),# Inelar
        (0, 17), (17, 18), (18, 19), (19, 20),# Mic
        (5, 9), (9, 13), (13, 17),             # Conexiuni palma
    ]
    for (a, b) in hand_base:
        edges.append((a + 33, b + 33))

    # === Right Hand (54-74) — offset 54 ===
    for (a, b) in hand_base:
        edges.append((a + 54, b + 54))

    # === Conexiuni mana <-> brat ===
    edges.append((15, 33))   # Incheietura stanga -> radacina mana stanga
    edges.append((16, 54))   # Incheietura dreapta -> radacina mana dreapta

    # Construieste matricea de adiacenta
    A = torch.zeros(num_joints, num_joints, dtype=torch.float32)
    for (i, j) in edges:
        if i < num_joints and j < num_joints:
            A[i, j] = 1.0
            A[j, i] = 1.0

    # Adauga self-loops
    A = A + torch.eye(num_joints, dtype=torch.float32)

    # Normalizare simetrica: D^{-1/2} A D^{-1/2}
    D = A.sum(dim=1)
    D_inv_sqrt = torch.diag(1.0 / torch.sqrt(D.clamp(min=1e-8)))
    A_norm = D_inv_sqrt @ A @ D_inv_sqrt

    return A_norm


class GraphConvolution(nn.Module):
    """Un singur strat de Graph Convolution."""

    def __init__(self, in_channels: int, out_channels: int, A: torch.Tensor,
                 num_subsets: int = 3):
        super().__init__()
        self.num_subsets = num_subsets

        # Parametri invatati pentru fiecare subset al grafului
        self.weights = nn.ParameterList([
            nn.Parameter(torch.empty(in_channels, out_channels))
            for _ in range(num_subsets)
        ])

        # Matricea de adiacenta adaptiva (se invata)
        self.register_buffer('A', A)
        self.adaptive_A = nn.Parameter(torch.zeros_like(A))

        # Batch norm + activare
        self.bn = nn.BatchNorm1d(out_channels)
        self.relu = nn.ReLU(inplace=True)

        self._init_weights()

    def _init_weights(self):
        for w in self.weights:
            nn.init.kaiming_uniform_(w, a=math.sqrt(5))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (B, J, C) — batch, joints, channels
        return: (B, J, C_out)
        """
        A = self.A + self.adaptive_A  # Adiacenta adaptiva
        A = F.softmax(A, dim=-1)

        out = torch.zeros(x.shape[0], x.shape[1], self.weights[0].shape[1],
                          device=x.device, dtype=x.dtype)

        for i, w in enumerate(self.weights):
            # Graph convolution: A @ X @ W
            h = torch.matmul(A, x)     # (B, J, C)
            h = torch.matmul(h, w)     # (B, J, C_out)
            out = out + h

        # BatchNorm pe channels: (B, J, C) -> (B, C, J) -> BN -> (B, J, C)
        out = out.transpose(1, 2)
        out = self.bn(out)
        out = out.transpose(1, 2)
        out = self.relu(out)

        return out


class SpatialGraphBlock(nn.Module):
    """Bloc spatial: GCN + rezidual."""

    def __init__(self, in_channels: int, out_channels: int, A: torch.Tensor,
                 dropout: float = 0.1):
        super().__init__()
        self.gcn = GraphConvolution(in_channels, out_channels, A)
        self.dropout = nn.Dropout(dropout)

        # Rezidual
        if in_channels != out_channels:
            self.residual = nn.Sequential(
                nn.Linear(in_channels, out_channels),
                nn.BatchNorm1d(out_channels)  # aplicat manual
            )
        else:
            self.residual = nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (B, J, C)"""
        if isinstance(self.residual, nn.Identity):
            res = x
        else:
            B, J, C = x.shape
            res = self.residual[0](x)           # (B, J, C_out)
            res = res.transpose(1, 2)
            res = self.residual[1](res)         # BN pe channels
            res = res.transpose(1, 2)

        out = self.gcn(x)
        out = self.dropout(out)
        return F.relu(out + res)


# =============================================================================
# 2. TEMPORAL CONVOLUTION — capteaza miscarea in timp
# =============================================================================

class TemporalConvBlock(nn.Module):
    """Bloc temporal cu dilated convolutions si rezidual."""

    def __init__(self, channels: int, kernel_size: int = 3, dilation: int = 1,
                 dropout: float = 0.1):
        super().__init__()
        padding = (kernel_size - 1) * dilation // 2

        self.conv = nn.Sequential(
            nn.Conv1d(channels, channels, kernel_size,
                      padding=padding, dilation=dilation),
            nn.BatchNorm1d(channels),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Conv1d(channels, channels, kernel_size,
                      padding=padding, dilation=dilation),
            nn.BatchNorm1d(channels),
        )
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (B, C, T)"""
        return self.relu(x + self.conv(x))


class MultiScaleTemporalConv(nn.Module):
    """Temporal Convolution multi-scala — capteaza miscari la viteze diferite."""

    def __init__(self, channels: int, num_scales: int = 4, dropout: float = 0.1):
        super().__init__()
        self.branches = nn.ModuleList([
            TemporalConvBlock(channels, kernel_size=3, dilation=2**i, dropout=dropout)
            for i in range(num_scales)
        ])
        self.fusion = nn.Sequential(
            nn.Conv1d(channels * num_scales, channels, 1),
            nn.BatchNorm1d(channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (B, C, T)"""
        outs = [branch(x) for branch in self.branches]
        out = torch.cat(outs, dim=1)  # (B, C*num_scales, T)
        return self.fusion(out)


# =============================================================================
# 3. TRANSFORMER ENCODER — atentie globala pe secventa
# =============================================================================

class PositionalEncoding(nn.Module):
    """Positional encoding sinusoidal."""

    def __init__(self, d_model: int, max_len: int = 500, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe.unsqueeze(0))  # (1, max_len, d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (B, T, D)"""
        x = x + self.pe[:, :x.size(1)]
        return self.dropout(x)


class TransformerEncoderBlock(nn.Module):
    """Transformer encoder cu pre-norm (mai stabil la antrenare)."""

    def __init__(self, d_model: int, nhead: int, dim_feedforward: int = 1024,
                 dropout: float = 0.1):
        super().__init__()
        self.norm1 = nn.LayerNorm(d_model)
        self.attn = nn.MultiheadAttention(d_model, nhead, dropout=dropout, batch_first=True)
        self.norm2 = nn.LayerNorm(d_model)
        self.ff = nn.Sequential(
            nn.Linear(d_model, dim_feedforward),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(dim_feedforward, d_model),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """x: (B, T, D)"""
        # Pre-norm self-attention
        h = self.norm1(x)
        h, _ = self.attn(h, h, h, key_padding_mask=mask)
        x = x + h
        # Pre-norm feedforward
        x = x + self.ff(self.norm2(x))
        return x


# =============================================================================
# 4. MODELUL COMPLET — SignTranslatorNet
# =============================================================================

class SignTranslatorNet(nn.Module):
    """
    Model complet pentru recunoastere limbaj al semnelor.

    Pipeline:
      Input (B, T, J, C) — secventa de keypoints
        |
        v
      [Spatial GCN] — intelege structura scheletului per frame
        |
        v
      [Multi-Scale TCN] — capteaza dinamica temporala
        |
        v
      [Transformer Encoder] — atentie globala pe secventa
        |
        v
      [Classification Head] — prezice gloss-ul
        |
        v
      Output (B, num_classes) — probabilitati per clasa
    """

    def __init__(self, in_channels: int = 3, num_joints: int = 75,
                 hidden_dim: int = 256, num_classes: int = 1926,
                 gcn_layers: int = 4, gcn_dropout: float = 0.1,
                 transformer_heads: int = 8, transformer_layers: int = 4,
                 transformer_dim: int = 256, transformer_dropout: float = 0.1,
                 transformer_ff_dim: int = 1024,
                 tcn_channels: list = None, num_scales: int = 4,
                 max_seq_len: int = 150):
        super().__init__()

        if tcn_channels is None:
            tcn_channels = [64, 128, 256]

        self.num_joints = num_joints
        self.hidden_dim = hidden_dim

        # Matricea de adiacenta a scheletului
        A = build_skeleton_adjacency(num_joints)
        self.register_buffer('A', A)

        # === Spatial GCN ===
        gcn_dims = [in_channels] + [hidden_dim // 2] * (gcn_layers - 1) + [hidden_dim]
        self.spatial_gcn = nn.ModuleList()
        for i in range(gcn_layers):
            self.spatial_gcn.append(
                SpatialGraphBlock(gcn_dims[i], gcn_dims[i + 1], A, dropout=gcn_dropout)
            )

        # === Joint pooling: J joints -> 1 vector per frame ===
        self.joint_pool = nn.Sequential(
            nn.Linear(num_joints * hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(gcn_dropout)
        )

        # === Multi-Scale Temporal Convolution ===
        self.temporal_conv = MultiScaleTemporalConv(
            hidden_dim, num_scales=num_scales, dropout=gcn_dropout
        )

        # === Transformer Encoder ===
        self.pos_encoding = PositionalEncoding(transformer_dim, max_len=max_seq_len * 2,
                                                dropout=transformer_dropout)
        self.transformer_layers = nn.ModuleList([
            TransformerEncoderBlock(
                transformer_dim, transformer_heads,
                dim_feedforward=transformer_ff_dim,
                dropout=transformer_dropout
            )
            for _ in range(transformer_layers)
        ])
        self.transformer_norm = nn.LayerNorm(transformer_dim)

        # === Classification Head ===
        self.classifier = nn.Sequential(
            nn.Linear(transformer_dim, transformer_dim),
            nn.GELU(),
            nn.Dropout(transformer_dropout),
            nn.Linear(transformer_dim, num_classes)
        )

        # Initializare
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.trunc_normal_(m.weight, std=0.02)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Conv1d):
                nn.init.kaiming_normal_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor,
                mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Args:
            x: (B, T, J, C) — batch, timp, joints, channels
            mask: (B, T) — True unde e padding (optional)

        Returns:
            logits: (B, num_classes)
        """
        B, T, J, C = x.shape

        # 1. Spatial GCN: proceseaza fiecare frame independent
        x = x.reshape(B * T, J, C)           # (B*T, J, C)
        for gcn in self.spatial_gcn:
            x = gcn(x)                         # (B*T, J, hidden_dim)

        # 2. Joint pooling: (B*T, J, H) -> (B*T, J*H) -> (B*T, H) -> (B, T, H)
        x = x.reshape(B * T, J * self.hidden_dim)
        x = self.joint_pool(x)                # (B*T, H)
        x = x.reshape(B, T, self.hidden_dim)  # (B, T, H)

        # 3. Multi-Scale Temporal Conv: (B, T, H) -> (B, H, T) -> TCN -> (B, T, H)
        x = x.transpose(1, 2)                 # (B, H, T)
        x = self.temporal_conv(x)              # (B, H, T)
        x = x.transpose(1, 2)                 # (B, T, H)

        # 4. Transformer Encoder
        x = self.pos_encoding(x)
        for layer in self.transformer_layers:
            x = layer(x, mask=mask)
        x = self.transformer_norm(x)

        # 5. Global pooling: medie peste timp (ignorand padding)
        if mask is not None:
            # mask: (B, T) — True = padding
            mask_expanded = (~mask).unsqueeze(-1).float()  # (B, T, 1), 1 = valid
            x = (x * mask_expanded).sum(dim=1) / mask_expanded.sum(dim=1).clamp(min=1)
        else:
            x = x.mean(dim=1)                 # (B, H)

        # 6. Clasificare
        logits = self.classifier(x)            # (B, num_classes)
        return logits

    def get_num_params(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def create_model(cfg) -> SignTranslatorNet:
    """Creeaza modelul din configurare."""
    model = SignTranslatorNet(
        in_channels=cfg.model.in_channels,
        num_joints=cfg.model.num_joints,
        hidden_dim=cfg.model.hidden_dim,
        num_classes=cfg.model.num_classes,
        gcn_layers=cfg.model.gcn_layers,
        gcn_dropout=cfg.model.gcn_dropout,
        transformer_heads=cfg.model.transformer_heads,
        transformer_layers=cfg.model.transformer_layers,
        transformer_dim=cfg.model.transformer_dim,
        transformer_dropout=cfg.model.transformer_dropout,
        transformer_ff_dim=cfg.model.transformer_ff_dim,
        num_scales=cfg.graph.num_scales,
        max_seq_len=cfg.data.max_seq_len,
    )
    return model
