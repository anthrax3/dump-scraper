#!/usr/bin/env bash
pyinstaller -y --onefile --noupx -c --distpath=../../release/linux --workpath=../tmp linux.dumpscraper.spec
cp ../templates/settings-dist.json ../../release/linux/settings-dist.json
cp ../templates/run_dumpscraper.sh ../../release/linux/run_dumpscraper.sh