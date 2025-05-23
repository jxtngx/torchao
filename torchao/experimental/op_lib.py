# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from pathlib import Path

import torch
from torch import Tensor
from torch.library import impl

# Load C++ ops - use multiple potential paths
potential_paths = [
    # Standard path from the module location
    Path(__file__).parent.parent,
    # Site-packages installation path
    Path(torch.__file__).parent.parent / "torchao",
    # For editable installs
    Path(__file__).parent.parent.parent / "torchao",
]


def find_and_load_libtorchao_ops(potential_paths):
    for lib_path in potential_paths:
        libs = list(lib_path.glob("libtorchao_ops_aten.*"))

        if not libs:
            continue

        assert len(libs) == 1, (
            f"Expected to find one libtorchao_ops_aten.* library at {lib_path}, but found {len(libs)}"
        )

        target_lib = libs[0]
        print(f"Found library at: {target_lib}")

        try:
            torch.ops.load_library(str(target_lib))
            return
        except Exception as e:
            print(f"Error loading library from {target_lib}: {e}")

    raise FileNotFoundError(
        "Could not find libtorchao_ops_aten library in any of the provided paths"
    )


find_and_load_libtorchao_ops(potential_paths)

# Define meta ops.  To support dynamic shapes, some meta ops need to
# be defined in python instead of C++.
torchao_lib = torch.library.Library("torchao", "IMPL")
for weight_nbit in range(1, 9):

    @impl(torchao_lib, f"_linear_8bit_act_{weight_nbit}bit_weight", "Meta")
    def _(
        activations: Tensor,
        packed_weights: Tensor,
        group_size: int,
        n: int,
        k: int,
    ):
        assert activations.dim() == 2
        m, k_ = activations.shape
        assert k_ == k
        return torch.empty(m, n, dtype=activations.dtype, device="meta")

    @impl(torchao_lib, f"_embedding_{weight_nbit}bit", "Meta")
    def _(
        packed_weight_qvals: Tensor,
        num_embeddings: int,
        embedding_dim: int,
        weight_scales: Tensor,
        weight_zeros: Tensor,
        indices: Tensor,
    ):
        assert indices.dim() == 1
        num_out = indices.shape[0]
        return torch.empty(num_out, embedding_dim, dtype=torch.float32, device="meta")

    @impl(torchao_lib, f"_shared_embedding_{weight_nbit}bit", "Meta")
    def _(packed_weights: Tensor, group_size: int, n: int, k: int, indices: Tensor):
        assert indices.dim() == 1
        num_out = indices.shape[0]
        return torch.empty(num_out, k, dtype=torch.float32, device="meta")
