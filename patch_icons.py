#!/usr/bin/env python3
"""Добавляет в Android-проект Capacitor выбор иконки приложения (обычная / микс).
Запускать из корня репозитория ПОСЛЕ создания папки android (npx cap add android / cap sync)."""
import glob, os, re, shutil, sys

MAIN = os.path.join("android", "app", "src", "main")
manifest = os.path.join(MAIN, "AndroidManifest.xml")
acts = glob.glob(os.path.join(MAIN, "java", "**", "MainActivity.java"), recursive=True)
if not os.path.exists(manifest) or not acts:
    sys.exit("android-проект не найден: запусти скрипт после создания папки android")
act = acts[0]
src = open(act, encoding="utf-8").read()
pkg = re.search(r"^\s*package\s+([\w.]+);", src, re.M).group(1)

# 1. иконки "микс" во всех плотностях
for d, sz in (("mdpi", 48), ("hdpi", 72), ("xhdpi", 96), ("xxhdpi", 144), ("xxxhdpi", 192)):
    dst = os.path.join(MAIN, "res", "mipmap-" + d)
    os.makedirs(dst, exist_ok=True)
    name = "ic_launcher_mix_%d.png" % sz
    srcp = next(q for q in (os.path.join("icons", name), name) if os.path.exists(q))
    shutil.copy(srcp, os.path.join(dst, "ic_launcher_mix.png"))

# 2. плагин, который включает нужный alias
plugin = '''package %s;

import android.content.ComponentName;
import android.content.pm.PackageManager;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "AppIcon")
public class AppIconPlugin extends Plugin {
    @PluginMethod
    public void setIcon(PluginCall call) {
        boolean mix = "mix".equals(call.getString("name", "default"));
        PackageManager pm = getContext().getPackageManager();
        String app = getContext().getPackageName();
        ComponentName def = new ComponentName(app, "%s.IconDefault");
        ComponentName mx = new ComponentName(app, "%s.IconMix");
        pm.setComponentEnabledSetting(mix ? mx : def, PackageManager.COMPONENT_ENABLED_STATE_ENABLED, PackageManager.DONT_KILL_APP);
        pm.setComponentEnabledSetting(mix ? def : mx, PackageManager.COMPONENT_ENABLED_STATE_DISABLED, PackageManager.DONT_KILL_APP);
        call.resolve();
    }
}
''' % (pkg, pkg, pkg)
open(os.path.join(os.path.dirname(act), "AppIconPlugin.java"), "w", encoding="utf-8").write(plugin)

# 3. регистрация плагина в MainActivity
if "AppIconPlugin" not in src:
    if "import android.os.Bundle;" not in src:
        src = re.sub(r"(package\s+[\w.]+;)", r"\1\n\nimport android.os.Bundle;", src, count=1)
    if re.search(r"onCreate\s*\(", src):
        src = re.sub(r"(void\s+onCreate\s*\([^)]*\)\s*\{)", r"\1\n        registerPlugin(AppIconPlugin.class);", src, count=1)
    else:
        src = re.sub(r"(extends\s+BridgeActivity\s*)\{\s*\}",
                     r"\1{\n    @Override\n    public void onCreate(Bundle savedInstanceState) {\n        registerPlugin(AppIconPlugin.class);\n        super.onCreate(savedInstanceState);\n    }\n}", src, count=1)
    assert "AppIconPlugin" in src, "не удалось изменить MainActivity.java"
    open(act, "w", encoding="utf-8").write(src)

# 4. manifest: убрать LAUNCHER у MainActivity и добавить два alias
m = open(manifest, encoding="utf-8").read()
if "IconMix" not in m:
    label = re.search(r'<activity[^>]*android:label="([^"]*)"', m)
    label = label.group(1) if label else "@string/app_name"
    m = re.sub(r'<intent-filter>\s*<action android:name="android\.intent\.action\.MAIN"\s*/>\s*<category android:name="android\.intent\.category\.LAUNCHER"\s*/>\s*</intent-filter>', "", m, count=1)
    def alias(name, icon, enabled):
        return ('\n        <activity-alias android:name="%s.%s" android:targetActivity="%s.MainActivity" android:enabled="%s" android:exported="true" android:icon="%s" android:label="%s">\n'
                '            <intent-filter>\n                <action android:name="android.intent.action.MAIN" />\n                <category android:name="android.intent.category.LAUNCHER" />\n            </intent-filter>\n        </activity-alias>\n') % (pkg, name, pkg, enabled, icon, label)
    m = m.replace("</application>", alias("IconDefault", "@mipmap/ic_launcher", "true") + alias("IconMix", "@mipmap/ic_launcher_mix", "false") + "    </application>", 1)
    open(manifest, "w", encoding="utf-8").write(m)
print("OK: иконки подключены, пакет", pkg)
