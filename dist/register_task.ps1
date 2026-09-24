
    $TaskName = "FreedomBlocker"
    $ExePath = "D:\Projects\freedom_blocker\dist\FreedomBlocker_v16.exe"
    $Arg = '--hidden'

    $Action = New-ScheduledTaskAction -Execute $ExePath -Argument $Arg
    
    # Trigger 1: At Logon
    $TrigLogon = New-ScheduledTaskTrigger -AtLogon
    
    # Trigger 2: At Startup (for robustness) - optional/skip
    
    # Settings: Hidden, RunLevel Highest, IgnoreNew execution
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Hidden -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew
    
    # Register
    # Note: We need to use -Force
    # We want repetition. It's easier to modify the trigger object after creation or use raw XML, but Let's try advanced properties.
    $TrigLogon.Repetition.Interval = "PT1M"
    $TrigLogon.Repetition.Duration = "P1D" # Re-triggers every logon anyway
    
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $TrigLogon -Settings $Settings -RunLevel Highest -User $env:USERNAME -Force
    