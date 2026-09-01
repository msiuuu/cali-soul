Set WshShell = CreateObject("WScript.Shell")
Dim key
key = WshShell.Environment("User")("OPENROUTER_API_KEY")
Dim cmd
cmd = "cmd /c ""cd /d C:\Users\yuscr\AppData\Local\Companion Emergence\python-runtime && set OPENROUTER_API_KEY=" & key & " && python.exe C:\Users\yuscr\debug_supervisor.py supervisor run --persona Cali --client-origin task-scheduler --idle-shutdown 0"""
WshShell.Run cmd, 0, False
WScript.Quit
