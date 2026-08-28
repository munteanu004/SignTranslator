import copy
import torch
import torch.nn as nn
from typing import Optional


def _get_clones(mod, n):
    return nn.ModuleList([copy.deepcopy(mod) for _ in range(n)])


class SPOTERTransformerDecoderLayer(nn.TransformerDecoderLayer):
    """TransformerDecoderLayer that skips the self-attention step.

    Original SPOTER deleted self_attn, but PyTorch 2.x accesses
    self_attn.batch_first before calling forward(), so we keep the
    module and simply skip it inside forward() instead.
    """

    def __init__(self, d_model, nhead, dim_feedforward, dropout, activation):
        super().__init__(d_model, nhead, dim_feedforward, dropout, activation)
                                                                              

    def forward(self, tgt: torch.Tensor, memory: torch.Tensor,
                tgt_mask: Optional[torch.Tensor] = None,
                memory_mask: Optional[torch.Tensor] = None,
                tgt_key_padding_mask: Optional[torch.Tensor] = None,
                memory_key_padding_mask: Optional[torch.Tensor] = None,
                tgt_is_causal: bool = False,
                memory_is_causal: bool = False) -> torch.Tensor:
                                                                 
        tgt = tgt + self.dropout1(tgt)
        tgt = self.norm1(tgt)
        tgt2 = self.multihead_attn(tgt, memory, memory, attn_mask=memory_mask,
                                   key_padding_mask=memory_key_padding_mask)[0]
        tgt = tgt + self.dropout2(tgt2)
        tgt = self.norm2(tgt)
        tgt2 = self.linear2(self.dropout(self.activation(self.linear1(tgt))))
        tgt = tgt + self.dropout3(tgt2)
        tgt = self.norm3(tgt)
        return tgt


class SPOTER(nn.Module):
    """
    SPOTER (Sign POse-based TransformER) for isolated sign language recognition.
    Input: (T, num_landmarks, 2) — T frames, each with X,Y coordinates per landmark.
    hidden_dim must equal num_landmarks * 2.
    """

    def __init__(self, num_classes: int, hidden_dim: int = 108):
        super().__init__()
        self.row_embed = nn.Parameter(torch.rand(50, hidden_dim))
        self.pos = nn.Parameter(
            torch.cat([self.row_embed[0].unsqueeze(0).repeat(1, 1, 1)], dim=-1)
            .flatten(0, 1).unsqueeze(0)
        )
        self.class_query = nn.Parameter(torch.rand(1, hidden_dim))
        self.transformer = nn.Transformer(hidden_dim, 9, 6, 6)
        self.linear_class = nn.Linear(hidden_dim, num_classes)

        custom_decoder = SPOTERTransformerDecoderLayer(
            self.transformer.d_model, self.transformer.nhead, 2048, 0.1, "relu"
        )
        self.transformer.decoder.layers = _get_clones(
            custom_decoder, self.transformer.decoder.num_layers
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
                                                                                                 
        h = torch.unsqueeze(inputs.flatten(start_dim=1), 1).float()
        h = self.transformer(self.pos + h, self.class_query.unsqueeze(0)).transpose(0, 1)
        return self.linear_class(h)
