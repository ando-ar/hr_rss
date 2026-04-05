@echo off
chcp 65001 > nul
echo.
echo HR tech 技術記事収集を開始します（過去7日間）...
echo.
uv run python -m hr_rss run
pause
