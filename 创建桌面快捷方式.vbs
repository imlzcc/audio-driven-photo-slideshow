Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = oWS.SpecialFolders("Desktop") & "\音频视频生成器.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "D:\app\audioToVideo\启动器.bat"
oLink.WorkingDirectory = "D:\app\audioToVideo"
oLink.Description = "音频驱动的图片幻灯片生成器"
oLink.Save
WScript.Echo "桌面快捷方式创建成功！"
