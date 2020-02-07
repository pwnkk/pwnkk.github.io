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

### 0x00 配置代理
需要的代理有两个
1. git 代理
`git config --global http.proxy http://ip:port`
2. bash 代理(给curl用)
```
export http_proxy="http://ip:port/"
export https_proxy=$http_proxy
```

### 0x01 编译安装

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

### 0x02 vscode + ccls

```
git clone https://github.com/MaskRay/ccls
cd ccls
# 在ccls根目录下执行
# 第0步，下载第三方依赖
git submodule update --init --recursive
# 第一步，下载llvm的二进制包
wget -c http://releases.llvm.org/8.0.0/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-18.04.tar.xz
# 解压二进制包
tar xf clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-18.04.tar.xz
# 在当前文件目录下执行cmake 执行结果保存到Release文件夹中
cmake -H. -BRelease -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=$PWD/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-18.04
cmake --build Release
# 开始编译并安装
cd Release
# 这里使用4线程编译，当然如果你的电脑够强的话，可以直接-j或者使用更搞核数加快编译
make -j4
# 编译完成，安装
sudo make install
```

### 34c3 v9 writeup

### 环境搭建




