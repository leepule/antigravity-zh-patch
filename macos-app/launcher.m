#import <Cocoa/Cocoa.h>

static NSString *runPythonCommand(NSString *scriptPath, NSArray<NSString *> *args, int *exitCode) {
    NSTask *task = [[NSTask alloc] init];
    task.launchPath = @"/usr/bin/python3";
    NSMutableArray *fullArgs = [NSMutableArray arrayWithObject:scriptPath];
    [fullArgs addObjectsFromArray:args];
    task.arguments = fullArgs;

    NSPipe *pipe = [NSPipe pipe];
    task.standardOutput = pipe;
    task.standardError = pipe;

    NSFileHandle *file = [pipe fileHandleForReading];
    [task launch];
    NSData *data = [file readDataToEndOfFile];
    [task waitUntilExit];

    if (exitCode) {
        *exitCode = [task terminationStatus];
    }
    return [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding] ?: @"";
}

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        NSApplication *app = [NSApplication sharedApplication];
        [app setActivationPolicy:NSApplicationActivationPolicyAccessory];
        [app activateIgnoringOtherApps:YES];

        NSBundle *bundle = [NSBundle mainBundle];
        NSString *resDir = [bundle resourcePath];
        NSString *patchScript = [resDir stringByAppendingPathComponent:@"patch.py"];
        NSString *iconPath = [resDir stringByAppendingPathComponent:@"icon.icns"];
        NSImage *appIcon = [[NSImage alloc] initWithContentsOfFile:iconPath];

        int statusExit = 0;
        NSString *jsonOut = runPythonCommand(patchScript, @[@"json-status"], &statusExit);
        NSData *jsonData = [jsonOut dataUsingEncoding:NSUTF8StringEncoding];
        NSDictionary *status = jsonData ? [NSJSONSerialization JSONObjectWithData:jsonData options:0 error:nil] : nil;

        BOOL exists = [status[@"exists"] boolValue];
        BOOL patched = [status[@"patched"] boolValue];
        BOOL integrityOk = [status[@"integrity_ok"] boolValue];
        BOOL hasBackup = [status[@"has_backup"] boolValue];
        NSString *version = status[@"version"] ?: @"未知";
        NSString *dictPath = status[@"dict_path"] ?: [resDir stringByAppendingPathComponent:@"zh-CN.json"];
        NSInteger exactCount = [status[@"exact_count"] integerValue];
        NSInteger patternCount = [status[@"pattern_count"] integerValue];

        NSAlert *alert = [[NSAlert alloc] init];
        if (appIcon) {
            alert.icon = appIcon;
        }
        alert.messageText = @"Antigravity 汉化助手";

        if (!exists) {
            alert.informativeText = @"未在 /Applications/Antigravity.app 找到应用，请确认已安装 Antigravity.app。";
            [alert addButtonWithTitle:@"关闭"];
            [alert runModal];
            return 0;
        }

        NSString *stateStr = patched ? @"已汉化 (简体中文)" : @"未汉化 (英文原版)";
        NSString *hashStr = integrityOk ? @"一致 (正常)" : @"不一致 (需重新应用)";
        alert.informativeText = [NSString stringWithFormat:
            @"目标应用：/Applications/Antigravity.app\n"
            @"当前版本：v%@\n"
            @"当前状态：%@\n"
            @"完整性校验：%@\n"
            @"词典规模：%ld 条精确词条 + %ld 条动态规则",
            version, stateStr, hashStr, (long)exactCount, (long)patternCount];

        NSString *primaryLabel = patched ? @"重新汉化 / 更新词典" : @"一键安装汉化";
        [alert addButtonWithTitle:primaryLabel];          // NSAlertFirstButtonReturn (1000)
        NSButton *restoreBtn = [alert addButtonWithTitle:@"还原英文原版"]; // NSAlertSecondButtonReturn (1001)
        if (!patched && !hasBackup) {
            restoreBtn.enabled = NO;
        }
        [alert addButtonWithTitle:@"编辑词典文件"];       // NSAlertThirdButtonReturn (1002)
        [alert addButtonWithTitle:@"关闭"];               // NSAlertThirdButtonReturn + 1 (1003)

        NSModalResponse resp = [alert runModal];

        if (resp == NSAlertFirstButtonReturn || resp == NSAlertSecondButtonReturn) {
            NSString *cmd = (resp == NSAlertFirstButtonReturn) ? @"install" : @"restore";
            int code = 0;
            NSString *output = runPythonCommand(patchScript, @[cmd], &code);

            NSAlert *doneAlert = [[NSAlert alloc] init];
            if (appIcon) {
                doneAlert.icon = appIcon;
            }
            if (code == 0) {
                doneAlert.messageText = (resp == NSAlertFirstButtonReturn)
                    ? @"汉化补丁安装成功！"
                    : @"已还原为英文原版！";
                doneAlert.informativeText = @"已自动同步更新 ASAR 完整性校验并完成 macOS 重签名。\n是否立即重启 Antigravity.app 以生效？";
                [doneAlert addButtonWithTitle:@"立即重启 Antigravity"];
                [doneAlert addButtonWithTitle:@"稍后手动重启"];
                if ([doneAlert runModal] == NSAlertFirstButtonReturn) {
                    NSTask *restartTask = [[NSTask alloc] init];
                    restartTask.launchPath = @"/bin/sh";
                    restartTask.arguments = @[@"-c", @"killall Antigravity >/dev/null 2>&1; sleep 1; open -a /Applications/Antigravity.app"];
                    [restartTask launch];
                }
            } else {
                doneAlert.alertStyle = NSAlertStyleCritical;
                doneAlert.messageText = @"执行出错";
                doneAlert.informativeText = output;
                [doneAlert addButtonWithTitle:@"确定"];
                [doneAlert runModal];
            }
        } else if (resp == NSAlertThirdButtonReturn) {
            int code = 0;
            NSString *userDictPath = [runPythonCommand(patchScript, @[@"prepare-user-dict"], &code)
                stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceAndNewlineCharacterSet]];
            NSString *targetDict = (userDictPath.length > 0) ? userDictPath : dictPath;
            [[NSWorkspace sharedWorkspace] activateFileViewerSelectingURLs:@[[NSURL fileURLWithPath:targetDict]]];
        }
    }
    return 0;
}
