---
layout: post
title:  "Android 逆向"
categories: REVERSE
tags: REVERSE
excerpt: Android app
mathjax: true
---

* content
{:toc}

## 0x00 app重打包
|功能|命令|
|--|--|
|解包|`apktool d ./com.hpplay.apk `|

解包后在 AndroidManifest.xml 中添加`android:debuggable="true"`

`<manifest xmlns:android="http://schemas.android.com/apk/res/android" android:debuggable="true"`

重打包 apktool b com.hpplay -o com.hpplay.back.apk

问题1 : `error: No resource identifier found for attribute `
解决: android:compileSdkVersion="27" 要低于28 , 修改后并没有解决问题

签名
```
keytool -genkey -keystore crack.keystore -keyalg RSA -validity 10000 -alias crack2
jarsigner -verbose -keystore crack.keystore -storepass 123456 -keypass 123456 -signedjar crackone_signed.apk  crackme-one-debug.apk crack2
```
