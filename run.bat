@echo off
chcp 65001 > nul
echo.
echo HR tech 技術記事収集を開始します（最新記事を全件取得）...
echo.
uv run hr-rss run
pause
