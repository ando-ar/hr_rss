@echo off
chcp 65001 > nul
echo.
echo HR tech 技術記事レポート生成
echo.
set /p DATE_FROM="開始日を入力してください (例: 2026-04-01): "
echo.
uv run hr-rss report --from "%DATE_FROM%"
pause
