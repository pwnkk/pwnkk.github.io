---
layout: post
title:  "Reverse tips"
categories: REVERSE
tags: REVERSE
excerpt: 记录逆向中的基础知识
mathjax: true
---

* content
{:toc}


### 蓝牙安全
蓝牙5.0 中推出了mesh 网络，用于实现网状拓补结构，和其他协议入zigbee 竞争市场。

### 哪里有问题
蓝牙是非常复杂的协议，并且被认为存在过度设计，wifi标准450页，而蓝牙标准有2822页。大量未经审计的功能设计都可能存在漏洞。矛盾在于对蓝牙标准的多种具体实现

![](IMG/Bluetooth/frag.png)

### 蓝牙协议简介

|协议版本|特点|传输速度|
| ---- | ---- | ---- |
|1.2 | Basic Rate (BR)| 1 Mbps|
|2.0 |  Enhanced Data Rate (EDR)|  3 Mbps|
|3.0 |  High Speed (HS)|  24 Mbps|
|4.0 |  Low Energy (BLE)| 1 Mbps|
|4.1 |  BLE/BR/EDR/HS | 1–3 Mbps|
|4.2 |   Gaussian frequency shift keying (GFSK) | 1 Mbps|


1. 蓝牙协议栈 

![](IMG/Bluetooth/Bluestack.png)

* L2CAP : Logical Link Control Adaptation Protocol
* RFCOMM : Radio Frequency Communications  
* LMP(Link Management Protocol) :负责管理蓝牙设备之间的通信，实现链路的建立、验证、链路配置等操作
* SDP : Service Discovery Protocol

其中Host Controller Interface 是蓝牙的命令接口，用于和基带,LMP交互。

蓝牙4协议栈
![](IMG/Bluetooth/blue4.png)

### 蓝牙安全

主要参考了两个标准 NIST 800-121-R1 和 IEEE 802.15.1. NIST 800-121-R1 details the recommended Bluetooth security processes. These recom