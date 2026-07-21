"""高中物理题库系统 - 预置题库数据

覆盖高中物理核心知识点，按年级分为高一高二和高三。
知识点结构采用二级分类：章 → 节。
"""

from database import Database
from models import Question
from datetime import datetime


def seed_all(db: Database):
    """导入所有预置数据"""
    print("📦 正在初始化题库...")
    seed_topics_and_questions(db)
    print(f"✅ 题库初始化完成！共 {db.count_questions()} 道题目")


def seed_topics_and_questions(db: Database):
    """创建知识点和预置题目"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ============================================================
    # 高一高二知识点
    # ============================================================

    # --- 必修1 ---
    t_motion_desc = db.add_topic("运动的描述", "高一高二")
    t_motion_desc_1 = db.add_topic("质点 参考系", "高一高二", t_motion_desc)
    t_motion_desc_2 = db.add_topic("位移 速度 加速度", "高一高二", t_motion_desc)

    t_linear = db.add_topic("匀变速直线运动", "高一高二")
    t_linear_1 = db.add_topic("基本公式与推论", "高一高二", t_linear)
    t_linear_2 = db.add_topic("自由落体与竖直上抛", "高一高二", t_linear)

    t_force = db.add_topic("相互作用——力", "高一高二")
    t_force_1 = db.add_topic("重力 弹力 摩擦力", "高一高二", t_force)
    t_force_2 = db.add_topic("力的合成与分解", "高一高二", t_force)

    t_newton = db.add_topic("牛顿运动定律", "高一高二")
    t_newton_1 = db.add_topic("牛顿三定律", "高一高二", t_newton)
    t_newton_2 = db.add_topic("超重与失重 连接体", "高一高二", t_newton)

    # --- 必修2 ---
    t_curve = db.add_topic("曲线运动", "高一高二")
    t_curve_1 = db.add_topic("运动的合成与分解", "高一高二", t_curve)
    t_curve_2 = db.add_topic("平抛运动", "高一高二", t_curve)

    t_circle = db.add_topic("圆周运动", "高一高二")
    t_circle_1 = db.add_topic("线速度与角速度", "高一高二", t_circle)
    t_circle_2 = db.add_topic("向心力与向心加速度", "高一高二", t_circle)

    t_gravity = db.add_topic("万有引力与航天", "高一高二")
    t_gravity_1 = db.add_topic("万有引力定律", "高一高二", t_gravity)
    t_gravity_2 = db.add_topic("宇宙速度与卫星", "高一高二", t_gravity)

    t_energy = db.add_topic("机械能守恒定律", "高一高二")
    t_energy_1 = db.add_topic("功和功率", "高一高二", t_energy)
    t_energy_2 = db.add_topic("动能定理与机械能守恒", "高一高二", t_energy)

    # --- 必修3 ---
    t_electric = db.add_topic("静电场", "高一高二")
    t_electric_1 = db.add_topic("库仑定律与电场强度", "高一高二", t_electric)
    t_electric_2 = db.add_topic("电势与电势差", "高一高二", t_electric)
    t_electric_3 = db.add_topic("电容器", "高一高二", t_electric)

    t_circuit = db.add_topic("电路及其应用", "高一高二")
    t_circuit_1 = db.add_topic("欧姆定律与电阻", "高一高二", t_circuit)
    t_circuit_2 = db.add_topic("串并联与电功率", "高一高二", t_circuit)

    # --- 选择性必修1 ---
    t_momentum = db.add_topic("动量守恒定律", "高一高二")
    t_momentum_1 = db.add_topic("冲量与动量定理", "高一高二", t_momentum)
    t_momentum_2 = db.add_topic("动量守恒与碰撞", "高一高二", t_momentum)

    t_wave = db.add_topic("机械振动与机械波", "高一高二")
    t_wave_1 = db.add_topic("简谐运动", "高一高二", t_wave)
    t_wave_2 = db.add_topic("波的图像与多普勒效应", "高一高二", t_wave)

    t_light = db.add_topic("光及其应用", "高一高二")
    t_light_1 = db.add_topic("折射与全反射", "高一高二", t_light)
    t_light_2 = db.add_topic("光的干涉与衍射", "高一高二", t_light)

    # --- 选择性必修2 ---
    t_magnetic = db.add_topic("安培力与洛伦兹力", "高一高二")
    t_magnetic_1 = db.add_topic("安培力", "高一高二", t_magnetic)
    t_magnetic_2 = db.add_topic("洛伦兹力与带电粒子运动", "高一高二", t_magnetic)

    # ============================================================
    # 高三知识点
    # ============================================================

    t_induction = db.add_topic("电磁感应", "高三")
    t_induction_1 = db.add_topic("法拉第电磁感应定律", "高三", t_induction)
    t_induction_2 = db.add_topic("楞次定律与自感", "高三", t_induction)

    t_ac = db.add_topic("交变电流", "高三")
    t_ac_1 = db.add_topic("变压器与远距离输电", "高三", t_ac)

    t_heat = db.add_topic("热学", "高三")
    t_heat_1 = db.add_topic("分子动理论", "高三", t_heat)
    t_heat_2 = db.add_topic("热力学定律与气体", "高三", t_heat)

    t_modern = db.add_topic("近代物理", "高三")
    t_modern_1 = db.add_topic("光电效应与波粒二象性", "高三", t_modern)
    t_modern_2 = db.add_topic("原子结构与核物理", "高三", t_modern)

    t_complex = db.add_topic("高考综合", "高三")
    t_complex_1 = db.add_topic("力学综合", "高三", t_complex)
    t_complex_2 = db.add_topic("电磁学综合", "高三", t_complex)

    # ============================================================
    # 预置题目
    # ============================================================

    questions = [
        # ============ 运动的描述 ============
        Question(topic_id=t_motion_desc_1, qtype="单选题", difficulty="易",
                 content="下列情况中，可以把物体看成质点的是（  ）",
                 options=["研究地球的自转", "研究火车通过一座桥梁的时间",
                          "研究乒乓球的旋转", "研究地球绕太阳的公转"],
                 answer="D",
                 explanation="当物体的形状、大小对所研究问题影响可忽略时可视为质点。地球绕太阳公转时地球大小可忽略。",
                 created_at=now),

        Question(topic_id=t_motion_desc_2, qtype="单选题", difficulty="易",
                 content="一个质点做直线运动，其位移随时间变化的关系为 x = 4t - t²（x的单位为m，t的单位为s），则质点的初速度和加速度分别为（  ）",
                 options=["4 m/s，-2 m/s²", "4 m/s，2 m/s²",
                          "-4 m/s，2 m/s²", "-4 m/s，-2 m/s²"],
                 answer="A",
                 explanation="与 x = v₀t + ½at² 对比可得 v₀=4 m/s，½a=-1 即 a=-2 m/s²。",
                 created_at=now),

        # ============ 匀变速直线运动 ============
        Question(topic_id=t_linear_1, qtype="单选题", difficulty="中",
                 content="一辆汽车以 20 m/s 的速度行驶，紧急刹车后加速度大小为 5 m/s²，则刹车后 6 s 内的位移是（  ）",
                 options=["30 m", "40 m", "50 m", "60 m"],
                 answer="B",
                 explanation="刹车时间 t₀=v₀/a=20/5=4s。6s>4s，汽车已停。x=v₀²/(2a)=400/10=40m。注意不能直接代入t=6s。",
                 created_at=now),

        Question(topic_id=t_linear_1, qtype="计算题", difficulty="中",
                 content="一物体做匀加速直线运动，初速度为 2 m/s，加速度为 0.5 m/s²。求：（1）物体在第3秒末的速度；（2）物体在前4秒内的位移。",
                 answer="（1）v = v₀ + at = 2 + 0.5×3 = 3.5 m/s\n（2）x = v₀t + ½at² = 2×4 + ½×0.5×16 = 8 + 4 = 12 m",
                 explanation="直接应用匀变速直线运动的速度公式和位移公式。",
                 created_at=now),

        Question(topic_id=t_linear_2, qtype="实验题", difficulty="中",
                 content="在「研究匀变速直线运动」的实验中，使用打点计时器得到一条纸带。已知打点周期为0.02s，相邻计数点间距分别为：s₁=1.20cm，s₂=2.00cm，s₃=2.80cm，s₄=3.60cm。求：（1）打第2个计数点时小车的瞬时速度；（2）小车运动的加速度大小。",
                 answer="（1）v₂=(s₂+s₃)/(2T)=(2.00+2.80)×10⁻²/(2×0.1)=0.24m/s\n（2）Δs=s₂-s₁=0.80cm，a=Δs/T²=0.80×10⁻²/0.01=0.80m/s²",
                 explanation="逐差法求加速度：a=(s₄+s₃-s₂-s₁)/(4T²) = (3.60+2.80-2.00-1.20)×10⁻²/(4×0.01)=0.80m/s²。",
                 created_at=now),

        # ============ 相互作用——力 ============
        Question(topic_id=t_force_1, qtype="单选题", difficulty="易",
                 content="关于摩擦力，下列说法正确的是（  ）",
                 options=["摩擦力总是阻碍物体的运动",
                          "静摩擦力的方向可能与物体运动方向相同",
                          "滑动摩擦力一定做负功",
                          "摩擦力的大小一定与正压力成正比"],
                 answer="B",
                 explanation="摩擦力阻碍的是相对运动（趋势），不是运动。静摩擦力方向可与运动方向相同（如物体放在加速的传送带上）。",
                 created_at=now),

        Question(topic_id=t_force_2, qtype="单选题", difficulty="中",
                 content="两个共点力的大小分别为 3 N 和 4 N，它们的合力大小不可能是（  ）",
                 options=["1 N", "5 N", "7 N", "8 N"],
                 answer="D",
                 explanation="合力的范围：|F₁-F₂| ≤ F ≤ F₁+F₂，即 1N ≤ F ≤ 7N。8N超出了最大值7N。",
                 created_at=now),

        # ============ 牛顿运动定律 ============
        Question(topic_id=t_newton_1, qtype="单选题", difficulty="中",
                 content="一个质量为 2 kg 的物体受到合外力 10 N 的作用，产生的加速度大小为（  ）",
                 options=["2 m/s²", "5 m/s²", "10 m/s²", "20 m/s²"],
                 answer="B",
                 explanation="根据牛顿第二定律 F=ma，a=F/m=10/2=5 m/s²。",
                 created_at=now),

        Question(topic_id=t_newton_2, qtype="计算题", difficulty="难",
                 content="质量为 m=60 kg 的人站在升降机中的体重计上。当升降机以加速度 a=2 m/s² 加速上升时，体重计的示数是多少？（取 g=10 m/s²）",
                 answer="720 N",
                 explanation="加速上升为超重状态。N-mg=ma，N=m(g+a)=60×(10+2)=720N。体重计示数对应支持力大小。",
                 created_at=now),

        # ============ 曲线运动 ============
        Question(topic_id=t_curve_1, qtype="单选题", difficulty="易",
                 content="关于曲线运动，下列说法正确的是（  ）",
                 options=["曲线运动的速度大小一定变化",
                          "曲线运动的加速度一定变化",
                          "曲线运动的速度方向一定变化",
                          "做曲线运动的物体所受合外力一定为变力"],
                 answer="C",
                 explanation="曲线运动的速度方向沿切线方向不断变化，但速度大小可以不变（如匀速圆周运动）。",
                 created_at=now),

        Question(topic_id=t_curve_2, qtype="计算题", difficulty="中",
                 content="从高为 20 m 的塔顶以 15 m/s 的初速度水平抛出一个小球。不计空气阻力，取 g=10 m/s²。求：（1）小球在空中运动的时间；（2）落地点与塔底的水平距离。",
                 answer="（1）t = √(2h/g) = √(40/10) = 2 s\n（2）x = v₀t = 15×2 = 30 m",
                 explanation="平抛运动分解为水平匀速直线运动和竖直自由落体运动。",
                 created_at=now),

        # ============ 圆周运动 ============
        Question(topic_id=t_circle_1, qtype="单选题", difficulty="中",
                 content="一质点做匀速圆周运动，半径为 r，周期为 T，则其线速度大小为（  ）",
                 options=["2πrT", "2πr/T", "r/T", "T/(2πr)"],
                 answer="B",
                 explanation="线速度 v = 周长/周期 = 2πr/T。",
                 created_at=now),

        Question(topic_id=t_circle_2, qtype="实验题", difficulty="中",
                 content="在「探究向心力大小与质量、角速度、半径的关系」实验中，使用向心力演示器。当两小球质量相同、转动半径相同时，发现左球角速度为右球的2倍时，左球受到的向心力是右球的几倍？由此可得出什么结论？",
                 answer="4倍。向心力与角速度的平方成正比（F=mω²r）。",
                 explanation="控制变量法：m、r相同，F∝ω²。ω变为2倍，F变为4倍。",
                 created_at=now),

        # ============ 万有引力与航天 ============
        Question(topic_id=t_gravity_1, qtype="单选题", difficulty="中",
                 content="两颗人造卫星A、B绕地球做匀速圆周运动，它们的轨道半径之比 rA:rB = 4:1，则它们的线速度之比 vA:vB 为（  ）",
                 options=["4:1", "2:1", "1:2", "1:4"],
                 answer="C",
                 explanation="由 GMm/r²=mv²/r 得 v=√(GM/r)，v∝1/√r。vA:vB=√(1/4):√1=1:2。",
                 created_at=now),

        Question(topic_id=t_gravity_2, qtype="实验题", difficulty="中",
                 content="在「用单摆测定重力加速度」实验中，测得摆长L=1.00m，用秒表测得单摆完成50次全振动的时间为100.5s。求：（1）单摆的周期；（2）由此测得的重力加速度g值（保留3位有效数字）。",
                 answer="（1）T=100.5/50=2.01s\n（2）g=4π²L/T²=4×3.14²×1.00/2.01²≈9.77m/s²",
                 explanation="单摆周期公式 T=2π√(L/g) → g=4π²L/T²。50次全振动取平均可减小测量误差。",
                 created_at=now),

        # ============ 机械能守恒定律 ============
        Question(topic_id=t_energy_1, qtype="单选题", difficulty="易",
                 content="一个力对物体做了 100 J 的功，则下列说法正确的是（  ）",
                 options=["物体的动能一定增加 100 J",
                          "物体的机械能一定增加 100 J",
                          "这个力一定是恒力",
                          "以上说法都不一定正确"],
                 answer="D",
                 explanation="合外力做功等于动能变化（动能定理）。单个力做功不一定全部转化为动能增加，可能转化为其他形式的能。",
                 created_at=now),

        Question(topic_id=t_energy_2, qtype="计算题", difficulty="中",
                 content="质量为 2 kg 的物体从距地面 10 m 高处自由下落。不计空气阻力，取 g=10 m/s²。求：（1）物体落地时的动能；（2）物体下落过程中重力势能的减少量。",
                 answer="（1）Ek = mgh = 2×10×10 = 200 J\n（2）ΔEp = mgh = 200 J",
                 explanation="机械能守恒：重力势能减少量等于动能增加量。Eₖ=mgh=200J。",
                 created_at=now),

        Question(topic_id=t_energy_2, qtype="单选题", difficulty="难",
                 content="一物体沿光滑斜面从静止开始下滑，当它滑到斜面底端时，速度大小为 v。若斜面倾角变为原来的 2 倍（高度不变），则物体滑到底端的速度大小为（  ）",
                 options=["v/2", "v", "√2v", "2v"],
                 answer="B",
                 explanation="机械能守恒 mgh=½mv²，v=√(2gh)。高度不变则速度不变，与倾角无关。",
                 created_at=now),

        # ============ 静电场 ============
        Question(topic_id=t_electric_1, qtype="单选题", difficulty="中",
                 content="真空中两个点电荷，相距为 r 时库仑力大小为 F。若将它们的电荷量都增大为原来的 2 倍，距离也增大为原来的 2 倍，则它们之间的库仑力大小为（  ）",
                 options=["F/4", "F", "2F", "4F"],
                 answer="B",
                 explanation="F=kq₁q₂/r²。F'=k(2q₁)(2q₂)/(2r)²=4kq₁q₂/4r²=F。不变。",
                 created_at=now),

        Question(topic_id=t_electric_1, qtype="单选题", difficulty="中",
                 content="在电场中某点放入电量为 q 的试探电荷时，测得该点场强为 E。若在同一点放入电量为 -2q 的试探电荷，则该点的场强（  ）",
                 options=["大小为 2E，方向与 E 相反",
                          "大小为 2E，方向与 E 相同",
                          "大小为 E，方向与 E 相反",
                          "大小和方向都不变"],
                 answer="D",
                 explanation="电场强度由电场本身决定，与试探电荷无关。该点场强大小和方向都不变。",
                 created_at=now),

        Question(topic_id=t_electric_2, qtype="实验题", difficulty="中",
                 content="在「用描迹法画出电场中一个平面上的等势线」实验中，使用导电纸、灵敏电流计和两个电极。当灵敏电流计的指针不偏转时，两探针所在位置的电势关系是什么？若要描绘出等差等势线，应如何操作？",
                 answer="指针不偏转时两点电势相等，即为等势点。移动探针找到一系列电流计指零的点，连成等势线；改变基准点位置可描绘不同电势的等势线。",
                 explanation="灵敏电流计在两点等电势时无电流通过。在导电纸上通过移动探针找到多个等势点，连成光滑曲线即为等势线。",
                 created_at=now),

        Question(topic_id=t_electric_3, qtype="单选题", difficulty="难",
                 content="一平行板电容器充电后与电源断开，将两极板间距增大，则（  ）",
                 options=["电容增大，电压减小", "电容减小，电压增大",
                          "电容不变，电压不变", "电容增大，电压不变"],
                 answer="B",
                 explanation="与电源断开后Q不变。C=εS/(4πkd)，d增大→C减小。U=Q/C，C减小→U增大。",
                 created_at=now),

        # ============ 电路及其应用 ============
        Question(topic_id=t_circuit_1, qtype="单选题", difficulty="易",
                 content="一段导体的电阻为 R，将其均匀拉长为原来的 2 倍后，其电阻变为（  ）",
                 options=["R/4", "R/2", "2R", "4R"],
                 answer="D",
                 explanation="R=ρL/S。长度变为2倍，截面积变为1/2倍，R'=ρ·2L/(S/2)=4ρL/S=4R。",
                 created_at=now),

        Question(topic_id=t_circuit_2, qtype="实验题", difficulty="中",
                 content="在「测定金属的电阻率」实验中，用螺旋测微器测得金属丝直径d=0.400mm，用毫米刻度尺测得接入电路的长度L=50.0cm。用伏安法测得电压U=2.00V，电流I=0.400A。求：（1）金属丝的电阻R；（2）该金属材料的电阻率ρ。",
                 answer="（1）R=U/I=2.00/0.400=5.00Ω\n（2）S=π(d/2)²=1.256×10⁻⁷m²，ρ=RS/L=5.00×1.256×10⁻⁷/0.500=1.26×10⁻⁶Ω·m",
                 explanation="电阻定律 R=ρL/S → ρ=RS/L。螺旋测微器估读到0.001mm。",
                 created_at=now),

        Question(topic_id=t_circuit_2, qtype="计算题", difficulty="中",
                 content="一个标有\"220V 100W\"的灯泡，求：（1）灯泡的电阻；（2）灯泡正常工作时的电流；（3）若将此灯泡接在 110V 的电路中，实际功率为多少？",
                 answer="（1）R=U²/P=220²/100=484Ω\n（2）I=P/U=100/220≈0.455A\n（3）P实=U实²/R=110²/484=25W",
                 explanation="灯泡电阻视为不变，实际功率与电压的平方成正比。",
                 created_at=now),

        # ============ 动量守恒定律 ============
        Question(topic_id=t_momentum_1, qtype="单选题", difficulty="中",
                 content="质量为 5 kg 的物体，以 10 m/s 的速度运动。若要使它在 2 s 内停下来，需要施加的平均阻力大小为（  ）",
                 options=["10 N", "25 N", "50 N", "100 N"],
                 answer="B",
                 explanation="动量定理：Ft=mv。F=mv/t=5×10/2=25N。",
                 created_at=now),

        Question(topic_id=t_momentum_2, qtype="单选题", difficulty="中",
                 content="两个质量相等的小球在光滑水平面上发生完全非弹性碰撞，碰撞前速度大小相等、方向相反，碰撞后（  ）",
                 options=["两球速度大小相等方向相反",
                          "两球都静止",
                          "两球以共同速度运动",
                          "无法确定"],
                 answer="B",
                 explanation="完全非弹性碰撞后黏在一起。动量守恒：mv+(-mv)=2mv'，v'=0。两球都静止。",
                 created_at=now),

        # ============ 机械振动与机械波 ============
        Question(topic_id=t_wave_1, qtype="单选题", difficulty="易",
                 content="关于简谐运动，下列说法正确的是（  ）",
                 options=["简谐运动是匀变速运动",
                          "振幅越大，周期越大",
                          "回复力方向始终指向平衡位置",
                          "回复力大小与位移成正比，方向相同"],
                 answer="C",
                 explanation="简谐运动中回复力F=-kx，方向始终指向平衡位置。周期与振幅无关，只与系统本身有关。",
                 created_at=now),

        Question(topic_id=t_wave_2, qtype="单选题", difficulty="中",
                 content="一列波在介质中传播，波速为 340 m/s，频率为 170 Hz，则该波的波长为（  ）",
                 options=["0.5 m", "1 m", "2 m", "4 m"],
                 answer="C",
                 explanation="v=λf → λ=v/f=340/170=2 m。",
                 created_at=now),

        # ============ 光及其应用 ============
        Question(topic_id=t_light_1, qtype="单选题", difficulty="中",
                 content="一束光从空气射入折射率为 √2 的玻璃中，入射角为 45°，则折射角为（  ）",
                 options=["30°", "45°", "60°", "90°"],
                 answer="A",
                 explanation="n=sin i/sin r，√2=sin45°/sin r=√2/2/sin r，sin r=1/2，r=30°。",
                 created_at=now),

        Question(topic_id=t_light_1, qtype="实验题", difficulty="中",
                 content="在「测定玻璃的折射率」实验中，用插针法测量。在玻璃砖一侧插入P₁、P₂两枚大头针，在另一侧透过玻璃砖观察，依次插入P₃、P₄使它们挡住P₁、P₂的像。若测得入射角i=45°，折射角r=30°，求玻璃的折射率。实验中若玻璃砖上下表面不平行，对测量结果有无影响？",
                 answer="n=sin i/sin r=sin45°/sin30°=√2≈1.41。玻璃砖上下表面不平行不影响折射率测量，因为只需测量一个界面的入射角和折射角。",
                 explanation="插针法原理：折射定律 n=sin i/sin r。玻璃砖的作用是提供两个界面，不平行只影响出射光线的偏移。",
                 created_at=now),

        Question(topic_id=t_light_2, qtype="单选题", difficulty="中",
                 content="在杨氏双缝干涉实验中，用单色光照射双缝，在屏上观察到干涉条纹。若将双缝间距减小，则（  ）",
                 options=["条纹间距变小", "条纹间距变大",
                          "条纹间距不变", "条纹消失"],
                 answer="B",
                 explanation="Δx=Lλ/d。d减小→Δx增大，条纹间距变大。",
                 created_at=now),

        # ============ 安培力与洛伦兹力 ============
        Question(topic_id=t_magnetic_1, qtype="单选题", difficulty="易",
                 content="一根长为 0.5 m 的通电直导线垂直放置在磁感应强度为 0.4 T 的匀强磁场中，导线中电流为 3 A，则导线受到的安培力大小为（  ）",
                 options=["0.2 N", "0.6 N", "1.2 N", "2.4 N"],
                 answer="B",
                 explanation="F=BIL=0.4×3×0.5=0.6 N。（B⊥I）",
                 created_at=now),

        Question(topic_id=t_magnetic_2, qtype="单选题", difficulty="难",
                 content="一个带电粒子以速度 v 垂直射入匀强磁场中做匀速圆周运动。若磁感应强度增大为原来的 2 倍，其他条件不变，则粒子圆周运动的周期变为原来的（  ）",
                 options=["1/4", "1/2", "2倍", "不变"],
                 answer="B",
                 explanation="T=2πm/(qB)。B增大为2倍→T减小为1/2倍。注意：速度v不变时半径r=mv/(qB)也减半。",
                 created_at=now),

        # ============ 高三 - 电磁感应 ============
        Question(topic_id=t_induction_1, qtype="单选题", difficulty="中",
                 content="一个闭合线圈放在变化的磁场中，线圈平面与磁场方向垂直。要使线圈中产生的感应电动势增大为原来的 2 倍，可以（  ）",
                 options=["将线圈匝数减小为原来的1/2",
                          "将磁通量的变化率增大为原来的2倍",
                          "将线圈面积减小为原来的1/2",
                          "将磁场方向改变90°"],
                 answer="B",
                 explanation="E=n·ΔΦ/Δt，感应电动势与磁通量变化率成正比。ΔΦ/Δt增大为2倍→E增大为2倍。",
                 created_at=now),

        Question(topic_id=t_induction_2, qtype="单选题", difficulty="中",
                 content="关于楞次定律，下列说法正确的是（  ）",
                 options=["感应电流的磁场方向总是与原磁场方向相反",
                          "感应电流的磁场总是阻碍引起感应电流的磁通量变化",
                          "感应电流的磁场总是增强原磁场",
                          "感应电流的方向与磁通量的变化快慢有关"],
                 answer="B",
                 explanation="楞次定律：感应电流的磁场总是阻碍引起感应电流的磁通量的变化（\"增反减同\"）。",
                 created_at=now),

        Question(topic_id=t_induction_1, qtype="计算题", difficulty="难",
                 content="一个匝数 n=100 的线圈，在 Δt=0.1 s 内磁通量从 0.02 Wb 均匀增加到 0.08 Wb。求：（1）线圈中产生的感应电动势大小；（2）若线圈电阻 R=2Ω，求感应电流大小。",
                 answer="（1）E=n·ΔΦ/Δt=100×(0.08-0.02)/0.1=100×0.6=60V\n（2）I=E/R=60/2=30A",
                 explanation="应用法拉第电磁感应定律 E=n·ΔΦ/Δt。",
                 created_at=now),

        # ============ 高三 - 交变电流 ============
        Question(topic_id=t_ac_1, qtype="单选题", difficulty="中",
                 content="理想变压器原线圈匝数为 1000 匝，副线圈匝数为 100 匝。原线圈接 220 V 交流电源，则副线圈输出电压为（  ）",
                 options=["11 V", "22 V", "110 V", "2200 V"],
                 answer="B",
                 explanation="U₁/U₂=n₁/n₂ → U₂=U₁×n₂/n₁=220×100/1000=22V。",
                 created_at=now),

        Question(topic_id=t_ac_1, qtype="实验题", difficulty="难",
                 content="在「探究变压器线圈两端的电压与匝数的关系」实验中，原线圈接学生电源交流挡，用多用电表交流电压挡测量原、副线圈电压。当原线圈匝数n₁=400，输入电压U₁=6.0V时，副线圈匝数n₂=100，测得副线圈电压U₂=1.4V。试分析：（1）为什么U₂小于理想值1.5V？（2）铁芯的作用是什么？",
                 answer="（1）实际变压器存在漏磁和铜损、铁损，效率<100%，所以U₂略小于理想值。（2）铁芯将原线圈的磁通量几乎全部导引到副线圈中，使两线圈磁通量变化相同，实现能量高效传递。",
                 explanation="理想变压器U₁/U₂=n₁/n₂，实际U₂=1.4V<1.5V，原因：漏磁、线圈电阻（铜损）、铁芯涡流（铁损）。",
                 created_at=now),

        # ============ 高三 - 热学 ============
        Question(topic_id=t_heat_1, qtype="单选题", difficulty="易",
                 content="关于分子动理论，下列说法正确的是（  ）",
                 options=["布朗运动就是液体分子的无规则运动",
                          "温度越高，分子的平均动能越大",
                          "分子间的引力和斥力都随距离增大而增大",
                          "0℃时物体分子的平均动能为零"],
                 answer="B",
                 explanation="温度是分子平均动能的标志。布朗运动是悬浮颗粒的无规则运动（反映了液体分子的运动）。分子间引力和斥力都随距离增大而减小。",
                 created_at=now),

        Question(topic_id=t_heat_2, qtype="单选题", difficulty="中",
                 content="一定质量的理想气体，在温度不变的条件下，体积增大为原来的 2 倍，则压强变为原来的（  ）",
                 options=["2倍", "1/2", "不变", "4倍"],
                 answer="B",
                 explanation="玻意耳定律：等温条件下 pV=常量。V→2V → p→p/2。",
                 created_at=now),

        # ============ 高三 - 近代物理 ============
        Question(topic_id=t_modern_1, qtype="单选题", difficulty="中",
                 content="关于光电效应，下列说法正确的是（  ）",
                 options=["只要入射光足够强，就一定能产生光电效应",
                          "光电子的最大初动能与入射光的强度成正比",
                          "光电子的最大初动能随入射光频率的增大而增大",
                          "光电效应的发生与入射光的频率无关"],
                 answer="C",
                 explanation="由爱因斯坦光电效应方程 Ek=hν-W₀，最大初动能随入射光频率增大而增大。发生条件：ν>ν₀（截止频率）。",
                 created_at=now),

        Question(topic_id=t_modern_2, qtype="单选题", difficulty="中",
                 content="一个氢原子从 n=3 的能级跃迁到 n=2 的能级，下列说法正确的是（  ）",
                 options=["氢原子吸收光子，能量增加",
                          "氢原子辐射光子，能量减少",
                          "氢原子吸收光子，能量减少",
                          "氢原子辐射光子，能量增加"],
                 answer="B",
                 explanation="从高能级跃迁到低能级，辐射光子，氢原子能量减少。",
                 created_at=now),

        Question(topic_id=t_modern_2, qtype="实验题", difficulty="中",
                 content="在「用双缝干涉测量光的波长」实验中，使用波长为λ的单色光照射双缝，双缝间距d=0.20mm，双缝到光屏的距离L=1.00m，测得相邻两条亮条纹中心间距Δx=3.00mm。求：（1）该单色光的波长λ；（2）若换用白光光源，中央亮条纹是什么颜色？",
                 answer="（1）λ=d·Δx/L=0.20×10⁻³×3.00×10⁻³/1.00=6.00×10⁻⁷m=600nm\n（2）中央亮条纹为白色（各色光在中央均为亮条纹，叠加为白色）。",
                 explanation="杨氏双缝干涉公式：Δx=Lλ/d。白光中各色光波长不同，除中央外其他级次条纹出现色散。",
                 created_at=now),

        # ============ 高三 - 高考综合 ============
        Question(topic_id=t_complex_1, qtype="计算题", difficulty="难",
                 content="如图所示，质量 m=2 kg 的物体从倾角 θ=37° 的斜面顶端由静止开始下滑，斜面长 L=5 m，物体与斜面间的动摩擦因数 μ=0.5。取 g=10 m/s²，sin37°=0.6，cos37°=0.8。求：（1）物体下滑过程中的加速度；（2）物体滑到斜面底端时的速度大小。",
                 answer="（1）mg sinθ - μmg cosθ = ma\na = g(sinθ - μcosθ) = 10×(0.6-0.5×0.8) = 10×(0.6-0.4) = 2 m/s²\n（2）v² = 2aL → v = √(2×2×5) = √20 ≈ 4.47 m/s",
                 explanation="这是力学综合题，需要用牛顿第二定律和运动学公式联合求解。",
                 created_at=now),

        Question(topic_id=t_complex_2, qtype="计算题", difficulty="难",
                 content="两平行金属板相距 d=5 cm，板间电压 U=200 V。一个电子（质量 m=9.1×10⁻³¹ kg，电荷量 e=1.6×10⁻¹⁹ C）从静止开始从负极板加速飞向正极板。求：（1）电子到达正极板时的速度大小；（2）若电子以该速度垂直射入磁感应强度 B=0.01 T 的匀强磁场中，电子做圆周运动的半径是多少？",
                 answer="（1）eU = ½mv² → v = √(2eU/m) = √(2×1.6×10⁻¹⁹×200/(9.1×10⁻³¹)) ≈ 8.4×10⁶ m/s\n（2）evB = mv²/r → r = mv/(eB) = 9.1×10⁻³¹×8.4×10⁶/(1.6×10⁻¹⁹×0.01) ≈ 4.8×10⁻³ m = 4.8 mm",
                 explanation="电场加速 + 磁场偏转的电磁学综合题。先用动能定理求速度，再用洛伦兹力提供向心力求半径。",
                 created_at=now),

        Question(topic_id=t_complex_1, qtype="单选题", difficulty="难",
                 content="一颗子弹水平射入静止在光滑水平面上的木块中并留在其中，下列说法正确的是（  ）",
                 options=["子弹减少的动能全部转化为木块的动能",
                          "子弹减少的动能等于木块增加的动能",
                          "子弹减少的动能大于木块增加的动能",
                          "系统的总动能保持不变"],
                 answer="C",
                 explanation="子弹射入木块是完全非弹性碰撞，系统动量守恒但机械能不守恒。子弹减少的动能一部分转化为木块动能，一部分转化为内能。",
                 created_at=now),

        # --- 补充题目以达到更好的覆盖 ---
        Question(topic_id=t_linear_1, qtype="单选题", difficulty="易",
                 content="一物体做匀变速直线运动，某时刻速度大小为 4 m/s，1 s 后速度大小变为 10 m/s，则在这 1 s 内该物体的（  ）",
                 options=["位移的大小可能小于 4 m",
                          "位移的大小可能大于 10 m",
                          "加速度的大小可能小于 4 m/s²",
                          "加速度的大小可能大于 10 m/s²"],
                 answer="D",
                 explanation="若速度反向变化：a=(10-(-4))/1=14 m/s² >10 m/s²，所以D正确。注意速度是矢量。",
                 created_at=now),

        Question(topic_id=t_newton_1, qtype="实验题", difficulty="中",
                 content="在「探究加速度与力、质量的关系」实验中，采用控制变量法。实验中得到的数据如下：保持小车质量M=0.50kg不变，改变砂桶质量，测得拉力F和加速度a分别为：F₁=0.10N, a₁=0.20m/s²；F₂=0.20N, a₂=0.38m/s²；F₃=0.30N, a₃=0.61m/s²。请分析：（1）a与F是否成正比？（2）实验中为何要求砂桶质量远小于小车质量？",
                 answer="（1）a/F比值分别为2.00、1.90、2.03，近似为常数，a与F近似成正比。（2）砂桶质量m≪M时，绳中拉力F≈mg，否则拉力小于mg，造成系统误差。",
                 explanation="牛顿第二定律F=Ma。实验中用mg近似替代拉力F，要求m≪M以减小系统误差。",
                 created_at=now),

        Question(topic_id=t_circle_2, qtype="单选题", difficulty="难",
                 content="一辆汽车通过拱形桥的最高点时，下列说法正确的是（  ）",
                 options=["汽车对桥的压力大于汽车的重力",
                          "汽车对桥的压力等于汽车的重力",
                          "汽车对桥的压力小于汽车的重力",
                          "无法确定"],
                 answer="C",
                 explanation="最高点时向心力向下：mg-N=mv²/r → N=mg-mv²/r < mg。汽车处于失重状态。",
                 created_at=now),

        # ============ 多选题（高一高二）============
        Question(topic_id=t_newton_1, qtype="多选题", difficulty="中",
                 content="关于力和运动的关系，下列说法正确的是（  ）",
                 options=["力是改变物体运动状态的原因",
                          "物体不受力时一定处于静止状态",
                          "物体运动不需要力来维持",
                          "力是维持物体运动的原因"],
                 answer="AC",
                 explanation="牛顿第一定律：力是改变运动状态的原因，运动不需要力维持。不受力时物体静止或匀速直线运动。",
                 created_at=now),

        Question(topic_id=t_energy_2, qtype="多选题", difficulty="中",
                 content="关于机械能守恒，下列说法正确的是（  ）",
                 options=["只有重力做功时，机械能守恒",
                          "物体在空气中匀速下落时机械能守恒",
                          "弹簧弹力做功时，系统机械能守恒",
                          "物体沿光滑斜面下滑时机械能守恒"],
                 answer="AD",
                 explanation="机械能守恒条件：只有重力或弹力做功。匀速下落有阻力，弹力做功需将弹性势能计入系统。",
                 created_at=now),

        Question(topic_id=t_curve_1, qtype="多选题", difficulty="中",
                 content="关于做曲线运动的物体，下列说法正确的是（  ）",
                 options=["速度方向一定变化",
                          "速度大小一定变化",
                          "所受合外力一定不为零",
                          "加速度方向与速度方向一定不在同一直线上"],
                 answer="ACD",
                 explanation="曲线运动速度方向必变；速度大小可不变（如匀速圆周）；合外力不为零；合外力方向与速度不共线。",
                 created_at=now),

        Question(topic_id=t_electric_1, qtype="多选题", difficulty="难",
                 content="关于电场，下列说法正确的是（  ）",
                 options=["电场强度为零的地方，电势一定为零",
                          "电场强度的方向是电势降低最快的方向",
                          "等势面上各点电场强度大小一定相等",
                          "电势越高的地方，正电荷具有的电势能越大"],
                 answer="BD",
                 explanation="E与φ无直接关系；E方向是电势降低最快的方向；等势面上E大小不一定相等；正电荷Ep=qφ，φ越大Ep越大。",
                 created_at=now),

        Question(topic_id=t_momentum_2, qtype="多选题", difficulty="中",
                 content="两物体在光滑水平面上发生碰撞，下列说法正确的是（  ）",
                 options=["碰撞前后系统的总动量守恒",
                          "碰撞前后系统的总动能一定守恒",
                          "弹性碰撞前后总动能守恒",
                          "完全非弹性碰撞后两物体速度相同"],
                 answer="ACD",
                 explanation="碰撞动量守恒；弹性碰撞动能守恒；非弹性碰撞动能不守恒；完全非弹性碰撞后共速。",
                 created_at=now),

        # ============ 多选题（高三）============
        Question(topic_id=t_induction_1, qtype="多选题", difficulty="难",
                 content="关于电磁感应现象，下列说法正确的是（  ）",
                 options=["穿过闭合回路的磁通量发生变化，回路中一定有感应电流",
                          "感应电流的磁场总是与原磁场方向相反",
                          "导体在磁场中做切割磁力线运动时一定产生感应电流",
                          "法拉第电磁感应定律表明感应电动势与磁通量变化率成正比"],
                 answer="AD",
                 explanation="楞次定律：感应磁场阻碍磁通量变化（增反减同），不是总相反。切割磁力线需闭合回路才有电流。",
                 created_at=now),

        Question(topic_id=t_modern_1, qtype="多选题", difficulty="中",
                 content="关于光电效应，下列说法正确的是（  ）",
                 options=["光电子的最大初动能与入射光频率成正比",
                          "入射光频率低于截止频率时，无论光强多大都不能产生光电效应",
                          "光电效应具有瞬时性",
                          "饱和光电流与入射光强度有关"],
                 answer="BCD",
                 explanation="Ek=hν-W₀，非正比关系。ν<ν₀时无光电效应（与光强无关）。光电效应瞬时发生。饱和电流∝光强。",
                 created_at=now),
    ]

    for q in questions:
        db.add_question(q)
