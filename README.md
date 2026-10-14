# cel-denoise

清理 AI 生图（GPT image）在赛璐璐 / 平涂风格大色块里留下的细噪点，并且不产生色带。

## 用法

```bash
uv run scripts/setup_waifu2x.py              # 每台机器一次：下载 waifu2x-ncnn-vulkan 到 bin/（不入库）
uv run scripts/clean.py 图1.png 图2.png       # 结果在 out/<名字>_clean.png
uv run scripts/analyze.py stats 原图.png out/原图_clean.png
uv run scripts/analyze.py board --box X,Y,边长 --out board.png 原图.png out/原图_clean.png
```

`clean.py` 参数：`--noise 0-3`（默认 3）、`--no-deband`、`--out DIR`。透明通道会保留。

## 流程

1. **waifu2x 降噪，不放大**：`-s 1 -n 3 -m models-cunet`。
2. **去色带**（`scripts/deband.py`）：在浮点下用 bilateral 只抹平 ±2.5 阶以内的台阶，边缘不动；再用随机 TPDF 抖动量化回 8-bit。

只做第 1 步会出问题。原图的细噪声本身在给平缓渐变做抖动，去掉以后渐变塌成 8-bit 台阶，形成一圈圈等高线，缩小看就是摩尔纹。第 2 步就是为此加的。

## 噪声是什么（以 noir 的 4 张 ChatGPT 图为样本，1254²）

- **溯源**：PNG 带 `caBX` 块，是 OpenAI 签名的 C2PA 清单，动作里有 `c2pa.watermarked.unbound`，也就是官方声明打了隐形水印。处理后的输出不再带这份清单（像素改了，原清单也会验签失败）。
- **细尺度噪声**：大色块内部的高频残差约 0.43 阶（8-bit）。肉眼几乎看不出，但放大后能看到斑驳纹理。
- **中尺度斑驳**：1.5–6px 频段约 0.8–1.1 阶。
- **不是 GPT 迷宫纹**：频谱单调下降，没有迷宫纹那种中频凸起和高频断崖。[repair-ai-image-quality](https://github.com/linsahdkadsa/repair-ai-image-quality) 会把这些图判为无迷宫纹并跳过。
- 衣服上肉眼可见的「脏」，主要来自 10–30px 的块状晕染阴影，幅度远大于噪点。本流程不处理这一层。要去掉它，只能让图像模型按平涂重绘，或者接受软阴影一起被抹平。

## 实测（`analyze.py stats`）

| | fill noise（<1.5px） | fill mottle（1.5–6px） | banding |
|---|---|---|---|
| 原图 16_42_28 | 0.46 | 1.13 | 0.47 |
| 只跑 waifu2x n3 | 0.23 | 1.14 | **0.65** |
| clean（n3 + 去色带） | 0.49 | 1.15 | 0.46 |
| 原图 16_46_39 | 0.43 | 0.82 | 0.59 |
| 只跑 waifu2x n3 | 0.16 | 0.69 | **0.79** |
| clean | 0.47 | 0.79 | 0.52 |

- 指标定义：fill noise 是平涂色块内 σ1.5 高通残差的标准差；fill mottle 是 σ1.5−σ6 带通的标准差；banding 是平缓渐变上水平相邻像素同值的比例，越高台阶越明显。
- clean 的 fill noise 回到原图水平，是抖动加回来的单像素白噪声，取代了原来成团的斑驳；这是不出等高线的代价。
- 1.5–6px 的斑驳只降了约 5%，现有手段都动不了它。

## 试过但不用的

| 方法 | 问题 |
|---|---|
| waifu2x n1 / n2 | 几乎没有效果。这两档针对的是 JPEG 噪声 |
| LAB bilateral（阈值 6） | 细颗粒能去掉，但会压出一块块色斑，色带最重（0.66） |
| ffmpeg `gradfun` 去色带 | 用的是有序抖动，留下规则网格，缩小后又出摩尔纹 |
| repair-ai-image-quality | 只认 GPT 迷宫纹，这类图会被跳过 |

## 其他现成方案

- [ComfyUI-GPT-Image-Latent-Refiner](https://github.com/AIEGOBOT/ComfyUI-GPT-Image-Latent-Refiner)：在 Qwen-Image / FLUX.2 / SDXL 的潜空间里修 GPT 的点状噪声，作者建议接在 SeedVR2 前面。需要 ComfyUI 和 GPU，未测。
- Real-CUGAN / Real-ESRGAN 动漫模型、OpenModelDB 上的 1x 降噪模型（用 chaiNNer 跑）：未测。

## License

[MIT](LICENSE)。waifu2x-ncnn-vulkan 由 `setup_waifu2x.py` 从上游下载，遵循其自身的 MIT 协议，不随本仓库分发。
