# STM32F103 Minimal System Board (PCB Design)

<!-- 封面大图 -->
![Cover](Images/stm32_front.png)

## 📖 简介 (Introduction)
这是一个基于 **STM32F103C8T6** 微控制器的最小系统板设计。
该项目使用 **EasyEDA (嘉立创EDA)** 设计，旨在为嵌入式初学者提供一个低成本、易于制作、引脚全引出的开发平台。

This is a minimal system board design based on the **STM32F103C8T6** microcontroller, designed with EasyEDA. It provides a low-cost, easy-to-build development platform with all pins broken out.

---

## ⚡ 特性 (Features)
- **核心控制器 (MCU)**: STM32F103C8T6 (ARM Cortex-M3, 72MHz, 64KB Flash, 20KB RAM)
- **供电系统 (Power)**: 
  - Type-C USB 接口 (5V 输入)
  - 板载 AMS1117-3.3 LDO (输出 3.3V，最大 800mA)
- **调试接口 (Debug)**: 标准 4-Pin SWD 接口 (VCC, DIO, CLK, GND)，支持 ST-Link / DAP-Link。
- **时钟系统 (Clock)**: 
  - 8MHz 高速晶振 (HSE)
  - 32.768kHz 低速晶振 (LSE - for RTC)
- **外设功能 (Peripherals)**:
  - **Reset Circuit**: 板载复位按键。
  - **Boot Config**: 通过跳线帽配置 BOOT0/BOOT1。
  - **LEDs**: 1x 电源指示灯 (Power), 1x 用户 LED (连接至 PC13)。
- **PCB 参数 (Specs)**: 
  - 尺寸：适合打样的常规尺寸
  - 层数：2 层
  - 工艺：推荐 1.6mm 板厚，绿色阻焊

---

## 📂 仓库文件结构 (File Structure)
```text
STM32F103-Minimal-System-PCB/
├── Hardware/          # EasyEDA 源文件 (.json / .eproj)
├── Fabrication/       # 生产文件 (Gerber, BOM, Pick&Place)
├── Images/            # 3D渲染图与原理图截图
└── README.md          # 项目说明文档
