@echo off
cd /d C:\Users\user\Desktop\OneDrive\Documents\SignTranslator\SignTranslatorExpo
start "" /b cmd /c "node_modules\.bin\expo.cmd start --clear --host lan --port 8088 > expo_8088.out.log 2> expo_8088.err.log"
