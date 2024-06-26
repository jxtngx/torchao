import torch
import torchao

from torchao.utils import benchmark_model, profiler_runner
from torchvision import models

torch.set_float32_matmul_precision("high")
# Load Vision Transformer model
model = models.vit_b_16(weights=models.ViT_B_16_Weights.IMAGENET1K_V1)

# Set the model to evaluation mode
model.eval().cuda().to(torch.bfloat16)

# Input tensor (batch_size, channels, height, width)
input_tensor = torch.randn(1, 3, 224, 224, dtype=torch.bfloat16, device='cuda')

## Quantization code - start
# int8 act, int8 weight dynamic quantization, see README for other APIs
torchao.apply_dynamic_quant(model)
## Quantization code - end

## compilation configs
torch._dynamo.config.automatic_dynamic_shapes = False
torch._inductor.config.force_fuse_int_mm_with_mul = True
torch._inductor.config.use_mixed_mm = True
## compilation configs end

model = torch.compile(model, mode='max-autotune')

# Must run with no_grad when optimizing for inference
with torch.no_grad():
    # warmup
    benchmark_model(model, 20, input_tensor)
    # benchmark
    print("elapsed_time: ", benchmark_model(model, 1000, input_tensor), " milliseconds")
    # Create a trace
    profiler_runner("quant.json.gz", benchmark_model, model, 5, input_tensor)
