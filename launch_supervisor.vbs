Set WshShell = CreateObject("WScript.Shell")
WshShell.Environment("Process")("OPENROUTER_API_KEY") = WshShell.Environment("User")("OPENROUTER_API_KEY")
WshShell.CurrentDirectory = "C:\Users\yuscr\AppData\Local\Companion Emergence\python-runtime"
WshShell.Run "python.exe C:\Users\yuscr\start_supervisor.py supervisor run --persona Cali --client-origin task-scheduler --idle-shutdown 0", 0, False
WScript.Quit
