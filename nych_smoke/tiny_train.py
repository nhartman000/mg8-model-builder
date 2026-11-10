"""Three CPU steps of the approved tiny shape on one English Common Corpus document.

This is not the V100 training run. The vocabulary is the tokens in that
document, because D14 leaves the vocabulary unfrozen. The learning rate,
the RoPE base, and the dropout site are smoke fixtures; the owner did not
set them. Training dropout 0.1 and inference dropout 0.0 are the approved
D9 values. The step count is three so the loop can be seen to run.
"""
from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn

from nych_smoke.pipeline import load_english_sample, run_text

D_MODEL = 128
N_LAYER = 2
N_HEAD = 4
HEAD_DIM = 32
FFN = 512
TRAIN_DROPOUT = 0.1
SMOKE_STEPS = 3
SMOKE_SEED = 0
SMOKE_LR = 1e-3
SMOKE_ROPE_BASE = 10000.0


class SmokeBlock(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.norm1 = nn.RMSNorm(D_MODEL)
        self.norm2 = nn.RMSNorm(D_MODEL)
        self.wq = nn.Linear(D_MODEL, D_MODEL, bias=False)
        self.wk = nn.Linear(D_MODEL, D_MODEL, bias=False)
        self.wv = nn.Linear(D_MODEL, D_MODEL, bias=False)
        self.wo = nn.Linear(D_MODEL, D_MODEL, bias=False)
        self.gate = nn.Linear(D_MODEL, FFN, bias=False)
        self.up = nn.Linear(D_MODEL, FFN, bias=False)
        self.down = nn.Linear(FFN, D_MODEL, bias=False)
        self.drop = nn.Dropout(TRAIN_DROPOUT)

    def forward(self, hidden: torch.Tensor) -> torch.Tensor:
        attended = self.drop(self._attend(self.norm1(hidden)))
        hidden = hidden + attended
        mixed = self.drop(self.down(F.silu(self.gate(self.norm2(hidden))) * self.up(self.norm2(hidden))))
        return hidden + mixed

    def _attend(self, hidden: torch.Tensor) -> torch.Tensor:
        length = hidden.shape[0]
        query = self._rope(self.wq(hidden).view(length, N_HEAD, HEAD_DIM))
        key = self._rope(self.wk(hidden).view(length, N_HEAD, HEAD_DIM))
        value = self.wv(hidden).view(length, N_HEAD, HEAD_DIM)
        scores = torch.einsum("thd,shd->hts", query, key) / (HEAD_DIM ** 0.5)
        causal = torch.triu(torch.ones(length, length, dtype=torch.bool), diagonal=1)
        scores = scores.masked_fill(causal, torch.finfo(scores.dtype).min)
        weights = torch.softmax(scores, dim=-1)
        mixed = torch.einsum("hts,shd->thd", weights, value).reshape(length, D_MODEL)
        return self.wo(mixed)

    def _rope(self, states: torch.Tensor) -> torch.Tensor:
        half = HEAD_DIM // 2
        positions = torch.arange(states.shape[0], dtype=torch.float32)
        freq = SMOKE_ROPE_BASE ** (-torch.arange(half, dtype=torch.float32) / half)
        angles = positions[:, None] * freq[None, :]
        cos = torch.cos(angles)[:, None, :]
        sin = torch.sin(angles)[:, None, :]
        first, second = states[..., :half], states[..., half:]
        return torch.cat((first * cos - second * sin, first * sin + second * cos), dim=-1)


class SmokeModel(nn.Module):
    def __init__(self, vocab: int) -> None:
        super().__init__()
        self.embed = nn.Embedding(vocab, D_MODEL)
        self.blocks = nn.ModuleList(SmokeBlock() for _ in range(N_LAYER))
        self.norm = nn.RMSNorm(D_MODEL)

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        hidden = self.embed(tokens)
        for block in self.blocks:
            hidden = block(hidden)
        return F.linear(self.norm(hidden), self.embed.weight)


def non_embedding_parameters(model: SmokeModel) -> int:
    tied = id(model.embed.weight)
    return sum(param.numel() for param in model.parameters() if id(param) != tied)


def train_sample(steps: int = SMOKE_STEPS) -> dict:
    if torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    sample = load_english_sample()
    report = run_text(sample["text"])
    surfaces = [token["text"] for token in report["tokens"]]
    vocab = {text: index for index, text in enumerate(dict.fromkeys(surfaces))}
    ids = torch.tensor([vocab[text] for text in surfaces], dtype=torch.long)
    torch.manual_seed(SMOKE_SEED)
    model = SmokeModel(len(vocab)).to(device)
    model.train()
    count = non_embedding_parameters(model)
    optimizer = torch.optim.Adam(model.parameters(), lr=SMOKE_LR)
    losses = []
    for _ in range(steps):
        optimizer.zero_grad(set_to_none=True)
        logits = model(ids.to(device))
        loss = F.cross_entropy(logits[:-1].float(), ids[1:].to(device))
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach().cpu()))
    model.eval()
    with torch.no_grad():
        held = model(ids.to(device))
        eval_loss = float(F.cross_entropy(held[:-1].float(), ids[1:].to(device)).cpu())
    return {
        "device": device,
        "cuda": bool(torch.cuda.is_available()),
        "v100": False,
        "steps": steps,
        "seed": SMOKE_SEED,
        "learning_rate": SMOKE_LR,
        "learning_rate_status": "smoke fixture, not an owner value",
        "rope_base": SMOKE_ROPE_BASE,
        "rope_base_status": "smoke fixture, not an owner value",
        "dropout_training": TRAIN_DROPOUT,
        "non_embedding_parameters": count,
        "vocab_size": len(vocab),
        "vocab_status": "tokens from this one document; D14 does not freeze a vocabulary",
        "identifier": sample["identifier"],
        "license": sample["license"],
        "language": sample["language"],
        "token_count": len(surfaces),
        "losses": losses,
        "eval_loss_dropout_off": eval_loss,
    }
