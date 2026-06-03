# Unmult 去黑批处理工具

这是一个本地美术小工具，用来把黑底素材转换成带透明通道的 PNG，适合发光、烟雾、火花、粒子、光效等素材。算法接近 AE 插件 Unmult：根据像素亮度反推 alpha，然后把颜色从黑底预乘状态中除回来。

源码版界面已调整为专业浅色工具风格：顶部是常用操作工具栏，左侧放导入、文件列表和调整参数，右侧放大预览、原图对比和导出设置，底部状态栏显示当前处理反馈。

当前源码版本：`1.0.0`。图形界面的“关于”窗口里可以点击“检查更新”，它会读取 GitHub Releases 中的最新版本。

## 发给同事的 exe 版本

当前仓库里的 `UnmultBatchTool.exe` 仍是旧二进制，尚未包含新的 UI、拖拽、滑杆和对比预览改动，暂时不要作为新版发给同事。

等源码版验收通过后，再单独做打包阶段生成新的 exe。到那时，同事在 Windows 上双击即可打开图形界面，不需要安装 Python。如果 Windows SmartScreen 提示未知发布者，选择“更多信息”，再选择“仍要运行”。这是因为 exe 没有做代码签名。

## 启动图形界面

源码版先安装依赖：

```powershell
python -m pip install -r .\requirements.txt
```

然后双击 `launch_unmult_tool.bat`，或在 PowerShell 中运行：

```powershell
python .\unmult_tool.py --gui
```

## 批量命令行

```powershell
python .\unmult_tool.py .\input_folder -o .\output_folder --recursive
```

常用参数：

- `--black-point 0`：低于此亮度的区域变为完全透明。
- `--white-point 255`：达到此亮度的区域变为完全不透明。
- `--gamma 1.0`：调整 alpha 曲线；大于 1 会让边缘更淡，小于 1 会保留更多边缘。
- `--mode max`：亮度算法。`max` 最接近常见光效素材；`luma` 更自然；`average` 更柔。
- `--suffix _unmult`：输出文件名后缀。
- `--overwrite`：覆盖输出目录中的同名 PNG。

## 支持格式

当前支持输入：PNG、JPG/JPEG、TIF/TIFF、BMP、WEBP。输出统一为 PNG。

DDS 暂时搁置，不在当前支持列表里。

## 使用建议

- 图形界面里的黑场、白场、Alpha Gamma 既可以拖动滑条，也可以在右侧输入框里手动输入精确数值，按 Enter 或点到别处后生效。
- 安装 `tkinterdnd2` 后，可以把多个图片或文件夹直接拖进窗口。
- 预览区右下角的“对比”按钮按住时显示原图，松开后恢复去黑预览。
- “关于”窗口中的“检查更新”只检查 GitHub Release 版本；当前仓库里的旧 exe 仍未重打包。
- 批处理时会跳过无法打开或处理失败的单个文件，并在完成后汇总成功和失败数量。
- 默认窗口尺寸下即可看到批量导出区域；旧 `UnmultBatchTool.exe` 尚未重新打包，当前新界面请通过源码版启动。
- 黑底干净的光效素材：先用默认 `max / 0 / 255 / 1.0`。
- 黑边残留：提高 `black-point`，例如 4 到 18。
- 边缘过硬：降低 `white-point` 或把 `gamma` 调到 1.2 到 1.8。
- 颜色发白或过曝：切到 `luma` 模式试试。
