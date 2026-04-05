from pathlib import Path
from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity

def main():
    print("🚀 启动前庭悬浮仿真测试...")
    
    # 1. 启动【平移】测试
    cfg_trans = GravityConfig(
        num_cells=800,
        t_end=0.6,
        disable_gravity=True,        # 开启悬浮模式
        vestibular_motion="translation" # 施加平移惯性
    )
    print("⏳ 正在运行平移 (Translation) 测试...")
    run_gravity(cfg_trans, save_outputs=True, outdir="outputs/vestibular_translation")
    
    # 2. 启动【旋转】测试
    cfg_rot = GravityConfig(
        num_cells=800,
        t_end=0.6,
        disable_gravity=True,        # 开启悬浮模式
        vestibular_motion="rotation"    # 施加旋转惯性
    )
    print("⏳ 正在运行旋转 (Rotation) 测试...")
    run_gravity(cfg_rot, save_outputs=True, outdir="outputs/vestibular_rotation")
    
    print("✅ 测试全部完成！结果已保存至 outputs/ 目录。")

if __name__ == "__main__":
    main()