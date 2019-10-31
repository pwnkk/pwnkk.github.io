---
layout: post
title:  "v8环境配置"
categories: pwn
tags: debug
excerpt: chrome v8 环境配置
mathjax: true
---

* content
{:toc}

### Overview

开始v8 引擎的环境搭建

### 配置代理
需要的代理有两个
1. git 代理
`git config --global http.proxy http://ip:port`
2. bash 代理(给curl用)
```
export http_proxy="http://ip:port/"
export https_proxy=$http_proxy
```

### 其他配置

安装depot_tools
```
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
echo 'export PATH=$PATH:"/path/to/depot_tools"' >> ~/.bashrc
```
安装ninja
```
git clone https://github.com/ninja-build/ninja.git
cd ninja && ./configure.py --bootstrap && cd ..
echo 'export PATH=$PATH:"/path/to/ninja"' >> ~/.bashrc
```
编译v8

```
fetch v8      #  下载v8代码
cd v8  
gclient sync  # 同步一下
tools/dev/v8gen.py x64.debug
ninja -C out.gn/x64.debug
```

### v9


