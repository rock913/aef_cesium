# Zero2x UI Assets (Landing Cinematic)

这个目录用于 Zero2x Landing 的“预告片质感”静态素材（优先 WebP，路径稳定、可离线）。

## 当前 Landing 使用的 4 张核心卡片 WebP

Landing 现在收敛为四张基座模型卡片（宏观：GeoGPT / OneAstronomy；微观：Genos / OnePorous）。对应背景图文件名固定为：

- `act2_geogpt.webp`
- `act2_astronomy.webp`
- `act3_genos.webp`
- `act3_oneporous.webp`

替换策略：保持文件名与路径不变，直接替换文件内容即可（建议 1920×1080，深色、强光影，文字区域有暗部）。

## 为什么“文件在仓库里但前端看不到”？

常见原因是你在 `frontend/public/` 下新增/替换了素材，但当前运行的是 **nginx / 静态 dist**：
它只会提供上一次构建出来的 `frontend/dist`，不会实时读取 `public/`。

解决：
- Docker prod/canary：重新 build 镜像（例如 `make docker-prod-up` 或 `make canary-rebuild-frontend`）
- 远程 nginx + release 模式：重新 `npm run build` 并把新的 `frontend/dist` 打包发布
