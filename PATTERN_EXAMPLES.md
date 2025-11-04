# 🎯 BEST PATTERN GENERATION EXAMPLES
# Showcasing Anchored + Multi-Segment Combinations

## 📊 SINGLE-STRING EXAMPLES (Best Matches)

================================================================================
✨ EXAMPLE 1: Multi-Segment Pattern - *array*sram*
================================================================================

GOAL: Select cache SRAM arrays, reject debug SRAMs and non-SRAM arrays

📥 INPUT (8 instances):
   soc/cpu_cluster/core0/l1_cache/instruction/tag_array/sram
   soc/cpu_cluster/core0/l1_cache/instruction/data_array/sram
   soc/cpu_cluster/core0/l1_cache/data/tag_array/sram
   soc/cpu_cluster/core0/l1_cache/data/data_array/sram
   soc/cpu_cluster/core1/l1_cache/instruction/tag_array/sram
   soc/cpu_cluster/core1/l1_cache/data/tag_array/sram
   soc/cpu_cluster/l2_cache/shared/tag_array/sram
   soc/cpu_cluster/l2_cache/shared/data_array/sram

✗ EXCLUDE (4 instances):
   soc/cpu_cluster/core0/debug/trace_buffer/sram           ← has "sram" but NOT "array"
   soc/cpu_cluster/core0/debug/breakpoint_unit/sram        ← has "sram" but NOT "array"
   soc/test_wrapper/bist/pattern_gen/cache_test/sram       ← has "sram" but NOT "array"
   soc/cpu_cluster/l2_cache/shared/tag_array/register_file ← has "array" but NOT "sram"

📤 OUTPUT:
   Pattern: *array*sram*
   Type: MULTI-SEGMENT (ordered keywords)

   🔗 Requires: 'array' → 'sram' (both keywords in order)

   ✅ Coverage:  8/8 (100%)
   ✅ False Pos: 0
   ✅ Wildcards: 3

💡 WHY THIS WINS:
   • Simple *sram* would match 3 debug excludes (FP=3) ❌
   • Simple *array* would match register_file exclude (FP=1) ❌
   • Multi-segment *array*sram* requires BOTH keywords → FP=0 ✅

   The ordered requirement filters out:
   - Paths with "sram" but no "array" (debug buffers)
   - Paths with "array" but no "sram" (register files)

================================================================================
✨ EXAMPLE 2: Pattern Combination - *retention*ram* | *backup*
================================================================================

GOAL: Select retention and backup RAMs in power domains, reject scratch/trace RAMs

📥 INPUT (6 instances):
   chip/power_domain_aon/rtc/calendar/backup_ram/cell0
   chip/power_domain_aon/rtc/calendar/backup_ram/cell1
   chip/power_domain_aon/pmu/state_machine/retention_ram/entry0
   chip/power_domain_aon/pmu/state_machine/retention_ram/entry1
   chip/power_domain_cpu/sleep_controller/wakeup_config/retention_ram/cell0
   chip/power_domain_cpu/sleep_controller/wakeup_config/retention_ram/cell1

✗ EXCLUDE (3 instances):
   chip/power_domain_aon/rtc/timer/scratch_ram/cell0        ← has "ram" but wrong type
   chip/power_domain_cpu/sleep_controller/debug/trace_ram/entry0 ← has "ram" but wrong type
   chip/power_domain_aon/pmu/retention_flops/data           ← has "retention" but NOT "ram"

📤 OUTPUT:
   Pattern 1: *retention*ram*  (MULTI-SEGMENT)
   Pattern 2: *backup*         (SUBSTRING)

   Combined Expression: *retention*ram* | *backup*

   🔗 Pattern 1 requires: 'retention' → 'ram' in order
   🔍 Pattern 2 matches: anywhere containing 'backup'

   ✅ Coverage:  6/6 (100%)
   ✅ False Pos: 0
   ✅ Wildcards: 5 (3 + 2)

💡 WHY THIS COMBINATION WORKS:
   • *retention*ram* covers 4 retention RAM instances
   • Avoids retention_flops by requiring both keywords
   • *backup* covers 2 backup RAM instances
   • Together they achieve complete coverage with zero FP

   Pattern 1 (multi-segment) provides precision
   Pattern 2 (substring) provides simplicity
   Best of both worlds!

================================================================================
✨ EXAMPLE 3: Three-Way Split - *fifo* | *buffer* | *command*
================================================================================

GOAL: Select APB peripheral memories (FIFOs, buffers, queues), reject AXI and config registers

📥 INPUT (9 instances):
   periph/uart0/apb_interface/tx_fifo/mem
   periph/uart0/apb_interface/rx_fifo/mem
   periph/uart1/apb_interface/tx_fifo/mem
   periph/uart1/apb_interface/rx_fifo/mem
   periph/spi0/apb_interface/tx_buffer/mem
   periph/spi0/apb_interface/rx_buffer/mem
   periph/spi1/apb_interface/tx_buffer/mem
   periph/i2c0/apb_interface/command_queue/mem
   periph/i2c0/apb_interface/data_buffer/mem

✗ EXCLUDE (3 instances):
   periph/dma/axi_interface/descriptor_queue/mem  ← AXI not APB
   periph/gpio/apb_interface/config_registers     ← register file not memory
   periph/uart0/baud_generator/divider_latch      ← not through apb_interface

📤 OUTPUT:
   Pattern 1: *fifo*    → 4 UART FIFOs
   Pattern 2: *buffer*  → 4 SPI/I2C buffers
   Pattern 3: *command* → 1 I2C command queue

   Combined: *fifo* | *buffer* | *command*

   ✅ Coverage:  9/9 (100%)
   ✅ False Pos: 0
   ✅ Wildcards: 6 (2 + 2 + 2)

💡 WHY THREE PATTERNS:
   • Could use one pattern: *apb*interface*mem* (4 wildcards)
   • But three patterns provide better semantic grouping:
     - *fifo* = UART FIFOs
     - *buffer* = SPI/I2C buffers
     - *command* = I2C queue
   • More understandable and maintainable
   • Each pattern is simpler than one complex multi-segment

================================================================================
✨ EXAMPLE 4: Prefix Pattern Victory - project/*
================================================================================

GOAL: Select all instances under project hierarchy

📥 INPUT (5 instances):
   project/module_a/subsys_x/component/memory/bank0
   project/module_a/subsys_x/component/memory/bank1
   project/module_a/subsys_y/component/memory/bank0
   project/module_b/subsys_x/logic/fifo
   project/module_b/subsys_y/logic/fifo

✗ EXCLUDE: (none in this example - showcasing efficiency)

📤 CANDIDATE ANALYSIS:
   Generated 34 total candidates:

   PREFIX:    project/*              score=10.5, wildcards=1 ⭐ WINNER
   SUBSTRING: *project*              score=7.0,  wildcards=2
   MULTI:     *module*subsys*        score=19.0, wildcards=3
   SUFFIX:    */bank0                score=6.0,  wildcards=1
   SUFFIX:    */fifo                 score=6.0,  wildcards=1

📤 OUTPUT:
   Pattern: project/*
   Type: PREFIX (anchored at START)

   ⚓ Anchored at beginning with 'project'

   ✅ Coverage:  5/5 (100%)
   ✅ False Pos: 0
   ✅ Wildcards: 1 (minimal!)

💡 WHY PREFIX WINS:
   • Fewest wildcards: 1 vs substring's 2
   • More specific: anchored at start
   • 1.5x score boost for being anchored
   • Most efficient pattern possible for this hierarchy

================================================================================


## 🏗️ MULTI-FIELD STRUCTURED EXAMPLES

================================================================================
✨ MULTI-FIELD EXAMPLE 1: SRAM Data Pins
================================================================================

GOAL: Select data pins (DIN/DOUT) on SRAM modules, reject control/address pins

📥 INPUT (10 instances with module/instance/pin fields):

Module         Instance                           Pin
---------      -------------------------------    --------
SRAM_512x64    chip/cpu/core0/l1_icache/bank0     DIN[0]
SRAM_512x64    chip/cpu/core0/l1_icache/bank0     DIN[63]
SRAM_512x64    chip/cpu/core0/l1_icache/bank0     DOUT[0]
SRAM_512x64    chip/cpu/core0/l1_icache/bank0     DOUT[63]
SRAM_512x64    chip/cpu/core0/l1_icache/bank1     DIN[0]
SRAM_512x64    chip/cpu/core0/l1_icache/bank1     DOUT[31]
SRAM_512x64    chip/cpu/core0/l1_dcache/bank0     DIN[15]
SRAM_512x64    chip/cpu/core0/l1_dcache/bank0     DOUT[15]
SRAM_512x64    chip/cpu/core0/l1_dcache/bank1     DIN[31]
SRAM_512x64    chip/cpu/core0/l1_dcache/bank1     DOUT[0]

✗ EXCLUDE (7 instances):

Module         Instance                           Pin
---------      -------------------------------    --------
SRAM_512x64    chip/cpu/core0/l1_icache/bank0     CLK     ← clock pin
SRAM_512x64    chip/cpu/core0/l1_icache/bank0     WEN     ← write enable
SRAM_512x64    chip/cpu/core0/l1_icache/bank0     CEN     ← chip enable
SRAM_512x64    chip/cpu/core0/l1_icache/bank0     ADDR[0] ← address pin
SRAM_512x64    chip/cpu/core0/l1_icache/bank0     ADDR[8] ← address pin
SRAM_512x64    chip/cpu/l2_cache/bank0            DIN[0]  ← L2 not L1
SRAM_512x64    chip/cpu/l2_cache/bank0            DOUT[0] ← L2 not L1

📤 IDEAL OUTPUT (What we want):
   Field: PIN
     Pattern 1: *DIN*
     Pattern 2: *DOUT*

   Field: INSTANCE
     Pattern: *l1*cache* (multi-segment - requires both keywords)

   Combined Logic:
     pin IN (*DIN*, *DOUT*) AND instance LIKE *l1*cache*

   This would give:
     ✅ All data pins on L1 cache SRAMs
     ❌ Rejects control pins (CLK, WEN, CEN, ADDR)
     ❌ Rejects L2 cache instances

💡 MULTI-FIELD POWER:
   • Can filter on EACH field independently
   • PIN pattern: *DIN* | *DOUT* (data pins only)
   • INSTANCE pattern: *l1*cache* (L1 caches only)
   • MODULE pattern: SRAM_* (SRAMs only)
   • THREE-DIMENSIONAL filtering!

================================================================================
✨ MULTI-FIELD EXAMPLE 2: AXI Interface Signals
================================================================================

GOAL: Select VALID signals on AXI_MASTER ports in CPU cluster

📥 INPUT (10 instances with module/instance/pin fields):

Module         Instance                              Pin
---------      ---------------------------------     --------
AXI_MASTER     soc/cpu_cluster/core0/axi_master_port AWVALID  (write address)
AXI_MASTER     soc/cpu_cluster/core0/axi_master_port WVALID   (write data)
AXI_MASTER     soc/cpu_cluster/core0/axi_master_port BVALID   (write response)
AXI_MASTER     soc/cpu_cluster/core0/axi_master_port ARVALID  (read address)
AXI_MASTER     soc/cpu_cluster/core0/axi_master_port RVALID   (read data)
AXI_MASTER     soc/cpu_cluster/core1/axi_master_port AWVALID
AXI_MASTER     soc/cpu_cluster/core1/axi_master_port ARVALID
AXI_MASTER     soc/cpu_cluster/core1/axi_master_port RVALID
AXI_MASTER     soc/cpu_cluster/dma/axi_master_port   AWVALID
AXI_MASTER     soc/cpu_cluster/dma/axi_master_port   ARVALID

✗ EXCLUDE (5 instances):

Module         Instance                              Pin
---------      ---------------------------------     --------
AXI_MASTER     soc/cpu_cluster/core0/axi_master_port AWREADY  ← READY not VALID
AXI_MASTER     soc/cpu_cluster/core0/axi_master_port ARREADY  ← READY not VALID
AXI_MASTER     soc/cpu_cluster/core0/axi_master_port WDATA[0] ← DATA not VALID
AXI_SLAVE      soc/cpu_cluster/l2_cache/axi_slave_port AWVALID ← SLAVE not MASTER
AXI_MASTER     soc/gpu_cluster/shader0/axi_master_port AWVALID ← GPU not CPU

📤 IDEAL OUTPUT (What we want):
   Field: MODULE
     Pattern: AXI_MASTER (exact match)

   Field: INSTANCE
     Pattern: *cpu_cluster* (substring)

   Field: PIN
     Pattern: *VALID (suffix - anchored at end)

   Combined Logic:
     module = 'AXI_MASTER'
     AND instance LIKE *cpu_cluster*
     AND pin LIKE *VALID

   This filters perfectly:
     ✅ Only AXI_MASTER modules (not AXI_SLAVE)
     ✅ Only cpu_cluster instances (not gpu_cluster)
     ✅ Only *VALID signals (not *READY or *DATA)
     ✅ THREE dimensions of filtering = ZERO false positives

💡 MULTI-FIELD PRECISION:
   • Each field provides an independent constraint
   • MODULE: Type filtering (master vs slave)
   • INSTANCE: Location filtering (cpu vs gpu)
   • PIN: Signal filtering (valid vs ready vs data)
   • Together: Precise multi-dimensional selection
   • IMPOSSIBLE to achieve with single-string patterns!

================================================================================


## 📊 PATTERN TYPE EFFECTIVENESS COMPARISON

================================================================================
Pattern Type    Format        Wildcards  Anchor   Use Case                    Example Result
--------------  ------------  ---------  -------  --------------------------  ------------------
PREFIX          token/*       1          Start    Top hierarchy               project/* → 5/5
SUFFIX          */token       1          End      Common endpoints            */fifo → 2/2
MULTI-SEGMENT   *a*b*         3+         None     Ordered keywords required   *array*sram* → 8/8
SUBSTRING       *token*       2          None     Flexible matching           *scheduler* → 8/8
EXACT           full/path     0          Both     Exact match                 soc/cpu/core0 → 1/1
COMBINATION     p1 | p2       varies     varies   Complex grouping            *retention*ram* | *backup* → 6/6
================================================================================


## 🎓 KEY LEARNINGS

1️⃣ MULTI-SEGMENT PATTERNS (*a*b*) EXCEL WHEN:
   ✅ Need multiple keywords together
   ✅ Simple substring causes false positives
   ✅ Order matters

   Example: *array*sram* vs *sram*
   - *sram* matches debug buffers (FP=3)
   - *array*sram* requires both → FP=0

2️⃣ ANCHORED PATTERNS (PREFIX/SUFFIX) ARE MORE EFFICIENT:
   ✅ Fewer wildcards (1 vs 2)
   ✅ More specific matching
   ✅ 1.5x score boost

   Example: project/* vs *project*
   - project/* → 1 wildcard
   - *project* → 2 wildcards
   - PREFIX wins!

3️⃣ PATTERN COMBINATIONS HANDLE COMPLEXITY:
   ✅ Different groups need different patterns
   ✅ Better semantic meaning
   ✅ Still maintains zero false positives

   Example: *retention*ram* | *backup*
   - Multi-segment for retention RAMs
   - Substring for backup RAMs
   - Together → complete coverage

4️⃣ MULTI-FIELD PATTERNS ENABLE THREE-DIMENSIONAL FILTERING:
   ✅ Filter on module type
   ✅ Filter on instance path
   ✅ Filter on pin name
   ✅ SIMULTANEOUSLY!

   Example: AXI VALID signals
   - module=AXI_MASTER (not SLAVE)
   - instance=*cpu_cluster* (not gpu)
   - pin=*VALID (not READY or DATA)
   - Result: Perfect precision

5️⃣ EXACT MODE GUARANTEES SAFETY:
   ✅ Zero false positives enforced
   ✅ May sacrifice coverage for precision
   ✅ Perfect for safety-critical selections


## 🚀 REAL-WORLD APPLICATIONS

✅ Clock Tree Analysis: All CK pins on DFF modules in execute stage
✅ Power Analysis: WEN pins on *SRAM* modules in *cache* instances
✅ Scan Chain: SO pins on SDFF modules in *crypto*encrypt* paths
✅ Interface Validation: *VALID pins on AXI_MASTER in *cpu_cluster*
✅ Timing Analysis: *result* paths in *execute*alu* | *execute*fpu*


================================================================================
All examples use EXACT mode (default) with zero false positives enforced! ✅
================================================================================
