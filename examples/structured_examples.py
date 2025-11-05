#!/usr/bin/env python3
"""
Structured Pattern Examples: Multi-Field Pattern Generation

Demonstrates pattern generation across structured data with fields:
- module: The leaf cell module name
- instance: The hierarchical instance path
- pin: The pin name on the module

Shows how the solver generates patterns per field and combines them.
"""
from patternforge.engine.models import SolveOptions
from patternforge.engine.solver import propose_solution_structured

def print_structured_example(title, include_rows, exclude_rows, description=""):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    if description:
        print(f"\n{description}")

    solution = propose_solution_structured(
        include_rows,
        exclude_rows,
        options=SolveOptions(splitmethod="classchange")
    )

    print(f"\n📥 INPUT:")
    print(f"  ✓ Include: {len(include_rows)} instances")
    print(f"\n  {'Module':<20} {'Instance':<40} {'Pin':<15}")
    print(f"  {'-'*20} {'-'*40} {'-'*15}")
    for row in include_rows[:10]:  # Show first 10
        print(f"  {row['module']:<20} {row['instance']:<40} {row['pin']:<15}")
    if len(include_rows) > 10:
        print(f"  ... and {len(include_rows) - 10} more")

    if exclude_rows:
        print(f"\n  ✗ Exclude: {len(exclude_rows)} instances")
        print(f"\n  {'Module':<20} {'Instance':<40} {'Pin':<15}")
        print(f"  {'-'*20} {'-'*40} {'-'*15}")
        for row in exclude_rows[:5]:
            print(f"  {row['module']:<20} {row['instance']:<40} {row['pin']:<15}")
        if len(exclude_rows) > 5:
            print(f"  ... and {len(exclude_rows) - 5} more")

    print(f"\n📤 OUTPUT:")
    print(f"  Expression: {solution.get('raw_expr', 'N/A')}")
    print(f"\n  📊 Metrics:")
    print(f"    Coverage:      {solution['metrics']['covered']}/{solution['metrics']['total_positive']} ({100*solution['metrics']['covered']/solution['metrics']['total_positive']:.0f}%)")
    print(f"    False Pos:     {solution['metrics']['fp']} ✅")
    print(f"    Patterns:      {solution['metrics']['atoms']}")
    print(f"    Wildcards:     {solution['metrics']['wildcards']}")

    atoms = solution.get('atoms', [])
    print(f"\n  🎯 Pattern Analysis ({len(atoms)} patterns):")

    # Group atoms by field
    by_field = {}
    for atom in atoms:
        field = atom.get('field') or 'ANY'
        if field not in by_field:
            by_field[field] = []
        by_field[field].append(atom)

    for field_name, field_atoms in by_field.items():
        print(f"\n    📌 Field: {field_name.upper()}")
        for i, atom in enumerate(field_atoms, 1):
            print(f"\n      [{i}] {atom['text']}")

            if atom['kind'] == 'prefix':
                print(f"          Type: PREFIX (anchored at start)")
                print(f"          ⚓ Matches {field_name} beginning with: {atom['text'].replace('/*', '')}")
            elif atom['kind'] == 'suffix':
                print(f"          Type: SUFFIX (anchored at end)")
                print(f"          ⚓ Matches {field_name} ending with: {atom['text'].replace('*/', '')}")
            elif atom['kind'] == 'multi':
                segments = [s for s in atom['text'].split('*') if s]
                print(f"          Type: MULTI-SEGMENT (ordered keywords)")
                print(f"          🔗 Requires in {field_name}: {' → '.join(repr(s) for s in segments)}")
            elif atom['kind'] == 'substring':
                print(f"          Type: SUBSTRING (flexible)")
                print(f"          🔍 Matches {field_name} containing: {atom['text'].strip('*')}")
            else:
                print(f"          Type: EXACT")

            print(f"          Wildcards: {atom['wildcards']}, Matches: {atom['tp']}, FP: {atom['fp']}")


print("=" * 80)
print("STRUCTURED PATTERN EXAMPLES: Multi-Field Pattern Generation")
print("=" * 80)
print("\nThese examples use structured data with three fields:")
print("  • module:   Leaf cell module name (e.g., 'SRAM_1024x32')")
print("  • instance: Hierarchical instance path (e.g., 'top/cpu/core0/cache')")
print("  • pin:      Pin name on the module (e.g., 'CLK', 'DIN[0]', 'Q[7]')")
print("\nThe solver generates patterns PER FIELD, creating sophisticated filters!")
print("=" * 80)

# Example 1: SRAM instances with data pins
print_structured_example(
    "EXAMPLE 1: SRAM Data Pins - Multi-Field Pattern (Module + Pin)",
    description="Goal: Select all data input/output pins on SRAM modules in L1 caches",
    include_rows=[
        # L1 instruction cache - SRAM banks
        {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_icache/bank0", "pin": "DIN[0]"},
        {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_icache/bank0", "pin": "DIN[63]"},
        {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_icache/bank0", "pin": "DOUT[0]"},
        {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_icache/bank0", "pin": "DOUT[63]"},
        {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_icache/bank1", "pin": "DIN[0]"},
        {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_icache/bank1", "pin": "DOUT[31]"},
        # L1 data cache - SRAM banks
        {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_dcache/bank0", "pin": "DIN[15]"},
        {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_dcache/bank0", "pin": "DOUT[15]"},
        {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_dcache/bank1", "pin": "DIN[31]"},
        {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_dcache/bank1", "pin": "DOUT[0]"},
    ],
    exclude_rows=[
        # SRAM control pins (not data)
        {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_icache/bank0", "pin": "CLK"},
        {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_icache/bank0", "pin": "WEN"},
        {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_icache/bank0", "pin": "CEN"},
        # SRAM address pins (not data)
        {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_icache/bank0", "pin": "ADDR[0]"},
        {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_icache/bank0", "pin": "ADDR[8]"},
        # L2 cache (wrong cache level)
        {"module": "SRAM_512x64", "instance": "chip/cpu/l2_cache/bank0", "pin": "DIN[0]"},
        {"module": "SRAM_512x64", "instance": "chip/cpu/l2_cache/bank0", "pin": "DOUT[0]"},
    ]
)

# Example 2: Register file read ports
print_structured_example(
    "EXAMPLE 2: Register File Read Ports - Instance Path Pattern",
    description="Goal: Select read port outputs on register files in decode stage",
    include_rows=[
        # Integer register file
        {"module": "REGFILE_32x64", "instance": "chip/cpu/core0/decode/int_rf", "pin": "RD0_DATA[0]"},
        {"module": "REGFILE_32x64", "instance": "chip/cpu/core0/decode/int_rf", "pin": "RD0_DATA[63]"},
        {"module": "REGFILE_32x64", "instance": "chip/cpu/core0/decode/int_rf", "pin": "RD1_DATA[0]"},
        {"module": "REGFILE_32x64", "instance": "chip/cpu/core0/decode/int_rf", "pin": "RD1_DATA[63]"},
        # FP register file
        {"module": "REGFILE_32x64", "instance": "chip/cpu/core0/decode/fp_rf", "pin": "RD0_DATA[31]"},
        {"module": "REGFILE_32x64", "instance": "chip/cpu/core0/decode/fp_rf", "pin": "RD1_DATA[31]"},
        # Core 1
        {"module": "REGFILE_32x64", "instance": "chip/cpu/core1/decode/int_rf", "pin": "RD0_DATA[15]"},
        {"module": "REGFILE_32x64", "instance": "chip/cpu/core1/decode/int_rf", "pin": "RD1_DATA[15]"},
    ],
    exclude_rows=[
        # Write ports (not read)
        {"module": "REGFILE_32x64", "instance": "chip/cpu/core0/decode/int_rf", "pin": "WR_DATA[0]"},
        {"module": "REGFILE_32x64", "instance": "chip/cpu/core0/decode/int_rf", "pin": "WR_DATA[63]"},
        # Read addresses (not data)
        {"module": "REGFILE_32x64", "instance": "chip/cpu/core0/decode/int_rf", "pin": "RD0_ADDR[4]"},
        # Different pipeline stage
        {"module": "REGFILE_32x64", "instance": "chip/cpu/core0/writeback/rename_rf", "pin": "RD0_DATA[0]"},
    ]
)

# Example 3: Flip-flop clock pins with multi-segment instance pattern
print_structured_example(
    "EXAMPLE 3: Clock Pins in Pipeline Stages - Multi-Segment Instance Pattern",
    description="Goal: Clock pins on flops in execute stage ALU units only",
    include_rows=[
        # ALU pipeline registers
        {"module": "DFF", "instance": "cpu/core0/execute/alu_int/stage1_reg/bit0", "pin": "CK"},
        {"module": "DFF", "instance": "cpu/core0/execute/alu_int/stage1_reg/bit1", "pin": "CK"},
        {"module": "DFF", "instance": "cpu/core0/execute/alu_int/stage2_reg/bit0", "pin": "CK"},
        {"module": "DFF", "instance": "cpu/core0/execute/alu_int/result_reg/bit0", "pin": "CK"},
        {"module": "DFF", "instance": "cpu/core0/execute/alu_int/result_reg/bit63", "pin": "CK"},
        # FPU pipeline registers
        {"module": "DFF", "instance": "cpu/core0/execute/fpu/stage1_reg/bit0", "pin": "CK"},
        {"module": "DFF", "instance": "cpu/core0/execute/fpu/stage2_reg/bit0", "pin": "CK"},
        {"module": "DFF", "instance": "cpu/core0/execute/fpu/result_reg/bit0", "pin": "CK"},
    ],
    exclude_rows=[
        # Data pins on same flops
        {"module": "DFF", "instance": "cpu/core0/execute/alu_int/stage1_reg/bit0", "pin": "D"},
        {"module": "DFF", "instance": "cpu/core0/execute/alu_int/stage1_reg/bit0", "pin": "Q"},
        # Decode stage (wrong pipeline stage)
        {"module": "DFF", "instance": "cpu/core0/decode/instruction_reg/bit0", "pin": "CK"},
        # Branch unit in execute (not ALU or FPU)
        {"module": "DFF", "instance": "cpu/core0/execute/branch_unit/prediction_reg/bit0", "pin": "CK"},
        # Debug registers
        {"module": "DFF", "instance": "cpu/core0/debug/execute_trace_reg/bit0", "pin": "CK"},
    ]
)

# Example 4: Complex multi-field with module type variations
print_structured_example(
    "EXAMPLE 4: Memory Modules with Write Enable - Module + Pin Pattern",
    description="Goal: Write enable pins on any memory module in cache subsystem",
    include_rows=[
        # Different SRAM sizes
        {"module": "SRAM_256x32", "instance": "soc/l1_cache/tag_array/bank0", "pin": "WEN"},
        {"module": "SRAM_256x32", "instance": "soc/l1_cache/tag_array/bank1", "pin": "WEN"},
        {"module": "SRAM_512x64", "instance": "soc/l1_cache/data_array/bank0", "pin": "WEN"},
        {"module": "SRAM_512x64", "instance": "soc/l1_cache/data_array/bank1", "pin": "WEN"},
        {"module": "SRAM_1024x128", "instance": "soc/l2_cache/data_array/bank0", "pin": "WEN"},
        {"module": "SRAM_1024x128", "instance": "soc/l2_cache/data_array/bank1", "pin": "WEN"},
        # Register file (also a memory)
        {"module": "REGFILE_32x64", "instance": "soc/l1_cache/mshr/entry_file", "pin": "WEN"},
    ],
    exclude_rows=[
        # Read enable (not write)
        {"module": "SRAM_256x32", "instance": "soc/l1_cache/tag_array/bank0", "pin": "REN"},
        # Data pins
        {"module": "SRAM_512x64", "instance": "soc/l1_cache/data_array/bank0", "pin": "DIN[0]"},
        # Non-cache memories
        {"module": "SRAM_256x32", "instance": "soc/debug/trace_buffer", "pin": "WEN"},
        {"module": "SRAM_512x64", "instance": "soc/test/mbist_mem", "pin": "WEN"},
    ]
)

# Example 5: Bus interface signals with complex grouping
print_structured_example(
    "EXAMPLE 5: AXI Master Interface Valid Signals - Multi-Field Combo",
    description="Goal: All valid signals on AXI master interfaces in CPU cluster",
    include_rows=[
        # AXI master ports - write channel
        {"module": "AXI_MASTER", "instance": "soc/cpu_cluster/core0/axi_master_port", "pin": "AWVALID"},
        {"module": "AXI_MASTER", "instance": "soc/cpu_cluster/core0/axi_master_port", "pin": "WVALID"},
        {"module": "AXI_MASTER", "instance": "soc/cpu_cluster/core0/axi_master_port", "pin": "BVALID"},
        # AXI master ports - read channel
        {"module": "AXI_MASTER", "instance": "soc/cpu_cluster/core0/axi_master_port", "pin": "ARVALID"},
        {"module": "AXI_MASTER", "instance": "soc/cpu_cluster/core0/axi_master_port", "pin": "RVALID"},
        # Core 1
        {"module": "AXI_MASTER", "instance": "soc/cpu_cluster/core1/axi_master_port", "pin": "AWVALID"},
        {"module": "AXI_MASTER", "instance": "soc/cpu_cluster/core1/axi_master_port", "pin": "ARVALID"},
        {"module": "AXI_MASTER", "instance": "soc/cpu_cluster/core1/axi_master_port", "pin": "RVALID"},
        # DMA engine
        {"module": "AXI_MASTER", "instance": "soc/cpu_cluster/dma/axi_master_port", "pin": "AWVALID"},
        {"module": "AXI_MASTER", "instance": "soc/cpu_cluster/dma/axi_master_port", "pin": "ARVALID"},
    ],
    exclude_rows=[
        # Ready signals (not valid)
        {"module": "AXI_MASTER", "instance": "soc/cpu_cluster/core0/axi_master_port", "pin": "AWREADY"},
        {"module": "AXI_MASTER", "instance": "soc/cpu_cluster/core0/axi_master_port", "pin": "ARREADY"},
        # Data signals
        {"module": "AXI_MASTER", "instance": "soc/cpu_cluster/core0/axi_master_port", "pin": "WDATA[0]"},
        # AXI slave (not master)
        {"module": "AXI_SLAVE", "instance": "soc/cpu_cluster/l2_cache/axi_slave_port", "pin": "AWVALID"},
        # Different cluster
        {"module": "AXI_MASTER", "instance": "soc/gpu_cluster/shader0/axi_master_port", "pin": "AWVALID"},
    ]
)

# Example 6: Complex scenario with all three fields having constraints
print_structured_example(
    "EXAMPLE 6: Scan Chain Outputs - Three-Field Pattern",
    description="Goal: Scan output pins on scan flops in crypto accelerator",
    include_rows=[
        # AES encryption pipeline
        {"module": "SDFF", "instance": "crypto/aes/encrypt/round0/sbox0/state_reg_0", "pin": "SO"},
        {"module": "SDFF", "instance": "crypto/aes/encrypt/round0/sbox0/state_reg_1", "pin": "SO"},
        {"module": "SDFF", "instance": "crypto/aes/encrypt/round0/sbox1/state_reg_0", "pin": "SO"},
        {"module": "SDFF", "instance": "crypto/aes/encrypt/round1/sbox0/state_reg_0", "pin": "SO"},
        {"module": "SDFF", "instance": "crypto/aes/encrypt/round1/sbox1/state_reg_0", "pin": "SO"},
        # SHA hash pipeline
        {"module": "SDFF", "instance": "crypto/sha256/hash/round0/adder/sum_reg_0", "pin": "SO"},
        {"module": "SDFF", "instance": "crypto/sha256/hash/round0/adder/sum_reg_1", "pin": "SO"},
        {"module": "SDFF", "instance": "crypto/sha256/hash/round1/adder/sum_reg_0", "pin": "SO"},
    ],
    exclude_rows=[
        # Scan input (not output)
        {"module": "SDFF", "instance": "crypto/aes/encrypt/round0/sbox0/state_reg_0", "pin": "SI"},
        # Functional data output
        {"module": "SDFF", "instance": "crypto/aes/encrypt/round0/sbox0/state_reg_0", "pin": "Q"},
        # Non-scan flops
        {"module": "DFF", "instance": "crypto/aes/encrypt/round0/sbox0/state_reg_0", "pin": "Q"},
        # Different module
        {"module": "SDFF", "instance": "cpu/core0/decode/instruction_reg_0", "pin": "SO"},
        # Key registers (not in encrypt/hash datapath)
        {"module": "SDFF", "instance": "crypto/aes/key_schedule/round_key_reg_0", "pin": "SO"},
    ]
)

# Example 7: Module prefix pattern with instance suffix pattern
print_structured_example(
    "EXAMPLE 7: Clock Gating Cells - Anchored Patterns on Multiple Fields",
    description="Goal: Output pins of clock gating cells in CPU cores only",
    include_rows=[
        # Core 0 clock gates
        {"module": "CKGT_STD", "instance": "chip/cpu/core0/fetch_unit/icache_cg", "pin": "GCLK"},
        {"module": "CKGT_STD", "instance": "chip/cpu/core0/decode_unit/regfile_cg", "pin": "GCLK"},
        {"module": "CKGT_STD", "instance": "chip/cpu/core0/execute_unit/alu_cg", "pin": "GCLK"},
        {"module": "CKGT_HIGH", "instance": "chip/cpu/core0/execute_unit/fpu_cg", "pin": "GCLK"},
        # Core 1 clock gates
        {"module": "CKGT_STD", "instance": "chip/cpu/core1/fetch_unit/icache_cg", "pin": "GCLK"},
        {"module": "CKGT_STD", "instance": "chip/cpu/core1/decode_unit/regfile_cg", "pin": "GCLK"},
        {"module": "CKGT_HIGH", "instance": "chip/cpu/core1/execute_unit/fpu_cg", "pin": "GCLK"},
    ],
    exclude_rows=[
        # Input clock (not gated output)
        {"module": "CKGT_STD", "instance": "chip/cpu/core0/fetch_unit/icache_cg", "pin": "CLK"},
        {"module": "CKGT_STD", "instance": "chip/cpu/core0/fetch_unit/icache_cg", "pin": "EN"},
        # GPU clock gates (different domain)
        {"module": "CKGT_STD", "instance": "chip/gpu/shader0/compute_cg", "pin": "GCLK"},
        # Memory controller clock gates
        {"module": "CKGT_STD", "instance": "chip/mem_ctrl/ddr_phy_cg", "pin": "GCLK"},
    ]
)

print("\n" + "=" * 80)
print("🎓 KEY INSIGHTS: Multi-Field Pattern Generation")
print("=" * 80)
print("""
STRUCTURED DATA PATTERNS enable sophisticated filtering across multiple fields:

1. PER-FIELD PATTERNS:
   - Each field (module, instance, pin) gets its own pattern
   - Example: module=*SRAM* AND instance=*cache* AND pin=*DIN*
   - Allows precise multi-dimensional filtering

2. PATTERN TYPES PER FIELD:
   - Module field: Often uses PREFIX (*SRAM*, *REGFILE*, *DFF*)
   - Instance field: Uses MULTI-SEGMENT (*execute*alu*, *l1*cache*)
   - Pin field: Uses SUFFIX (*/VALID, */CK) or SUBSTRING (*DATA*)

3. MULTI-SEGMENT PATTERNS IN INSTANCE PATHS:
   - *execute*alu* matches: cpu/core0/execute/alu_int/stage1_reg
   - Rejects: cpu/core0/decode/alu_bypass (missing "execute")
   - Rejects: cpu/core0/execute/branch_unit (missing "alu")

4. COMBINING FIELD PATTERNS:
   - Pattern on module: SRAM_* (prefix on module name)
   - Pattern on instance: *cache* (substring in path)
   - Pattern on pin: *DIN* | *DOUT* (data pins only)
   - Result: Data pins on SRAMs in caches only!

5. EXACT MODE WITH MULTIPLE FIELDS:
   - Zero false positives enforced across ALL field combinations
   - More powerful than single-string patterns
   - Semantic grouping by hardware structure

REAL-WORLD APPLICATIONS:
- Clock tree analysis: All clock pins in specific domains
- Power analysis: Write enables on memories in active domains
- Scan chain generation: Scan flops in specific modules
- Interface validation: Protocol signals on specific interfaces
- Timing analysis: Critical paths through specific units

The structured solver creates the minimal pattern set that precisely
captures your multi-dimensional selection criteria! ✨
""")
print("=" * 80)
