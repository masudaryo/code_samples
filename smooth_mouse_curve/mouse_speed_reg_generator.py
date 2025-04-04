import math
import itertools
from collections.abc import Sequence, Iterable
import matplotlib.pyplot as plt
from typing import Self


coefficient: float = 1.25
screen_dpi: float = 192


class SmoothMouseCurve:
    def __init__(self, x: Iterable[float], y: Iterable[float]):
        self.x: list[float] = list(x)
        self.y: list[float] = list(y)
        if len(self.x) != 5 or len(self.y) != 5:
            raise Exception("The lengths of x and y are must be 5.")
        if max(self.x + self.y) > 2**14:
            raise Exception("The values of x and y are must be <= 2**14")

    @classmethod
    def from_gradients_and_x(cls, gradients: Sequence[float], three_x: Sequence[float]) -> Self:
        if len(gradients) != 4 or len(three_x) != 3:
            raise Exception("gradients or three_x has invalid length")
        x = [0, *three_x]
        if x[-1] < 40:
            x.append(40)  # デフォルト設定の値
        else:
            x.append(x[-1] + 1)
        prev = 0
        y: list[float] = [0.0] + [
            prev := prev + grad * (x_2 - x_1) for x_1, x_2, grad in zip(x[:-1], x[1:], gradients)
        ]  # 0.にしないとpylanceに怒られる
        # 2**15が最大値と思われるがマージンを考えて2**13, 2**14を使う。
        if max(y[:-1]) > 2**13:
            raise Exception(f"{y[:-1] = }. y[:-1] must be < 2**13")
        elif y[-1] > 2**14:
            y[-1] = y[-2] + (2**14 - y[-2]) / 2
            x[-1] = x[-2] + (2**14 - y[-2]) / 2 / gradients[-1]
        return cls(x, y)

    @classmethod
    def from_coordinates(cls, coordinates: Sequence[Sequence[float]]) -> Self:
        return cls(*zip(*coordinates))

    @classmethod
    def from_points_and_x(
        cls,
        points: Sequence[Sequence[float]],
        three_x: Sequence[float],
        remaining_gradients: Sequence[float] | None = None,
    ):
        """len(points) = 4. three_xで定まる4つの各（半）区間がpointsの各点を通るようにcurveを定める。
        points[0][0] < three_x[0] < points[1][0] < three_x[1] < points[2][0] < three_x[2] < points[3][0]
        """
        if len(points) < 4:
            if remaining_gradients is None:
                raise Exception
            if len(points) + len(remaining_gradients) != 4:
                raise Exception
        elif len(points) > 4:
            raise Exception
        if len(three_x) != 3:
            raise Exception
        if not (points[0][0] < three_x[0] and all(x < p[0] for x, p in zip(three_x, points[1:]))):
            # if points[0][0] < three_x[0] < points[1][0] < three_x[1] < points[2][0] < three_x[2] < points[3][0]):
            raise Exception

        prev_x_y = (0, 0)
        gradients = []
        for prev_x, point, next_x in zip([0, *three_x], points, [*three_x, None]):
            gradient = (point[1] - prev_x_y[1]) / (point[0] - prev_x_y[0])
            gradients.append(gradient)
            if next_x is not None:
                prev_x_y = (next_x, prev_x_y[1] + gradient * (next_x - prev_x))

        if remaining_gradients is not None:
            return cls.from_gradients_and_x([*gradients, *remaining_gradients], three_x)
        else:
            return cls.from_gradients_and_x(gradients, three_x)

    def get_coordinates(self) -> list[list[float]]:
        return [list(coord) for coord in zip(self.x, self.y)]

    def get_gradients_and_x(self) -> tuple[list[float], list[float]]:
        coordinates = self.get_coordinates()
        gradients = [(p_2[1] - p_1[1]) / (p_2[0] - p_1[0]) for p_1, p_2 in zip(coordinates[:-1], coordinates[1:])]
        x_s = self.x[1:4].copy()
        return gradients, x_s

    def calc_mouse_count_to_pointer_count(self, mouse_count_x, mouse_count_y) -> tuple[float, float]:
        # この計算において、最初の傾き変更点より手前で、in:(2,2)->out:(4,4)に合わせたとしたら、in:(2,0)->out:(4,0), in:(1,1)->out:(2,2)のように入力countと出力countは方向によらず比例する。これは以下の計算で、最終的にscaleを各方向の入力countにかけて各方向の出力countを出力している、かつ最初の傾き変更点より手前ではグラフは線形であり、scaleはこの線形な部分の傾きの定数倍となり、入力countによらず一定になるからである。
        mouse_count = mouse_count_norm(mouse_count_x, mouse_count_y)
        mouse_speed = mouse_count / 3.5
        applied_speed = self.calc_applied_speed(mouse_speed)
        pointer_count = applied_speed * screen_dpi / 150
        scale = pointer_count / mouse_count * coefficient
        # print(f"{mouse_count=}, {mouse_speed=}, {applied_speed=}, {pointer_count=}, {scale=}, {self.x=}, {self.y=}")
        return mouse_count_x * scale, mouse_count_y * scale

    def calc_applied_speed(self, mouse_speed: float) -> float:
        """mouse_speedにこのcurveが表す関数を適用する"""
        gradients, _ = self.get_gradients_and_x()
        applied_speed = 0
        for grad, x_1, x_2, y_1 in zip(gradients, self.x[:-1], self.x[1:], self.y[:-1]):
            if mouse_speed < x_2:
                applied_speed = y_1 + (mouse_speed - x_1) * grad
                break
        else:
            applied_speed = self.y[-1] + (mouse_speed - self.x[-1]) * gradients[-1]
        return applied_speed

    def print_measured_count_analysis(
        self, measured_mouse_count_x, measured_mouse_count_y, measured_poiner_count_x, measured_pointer_count_y
    ):
        """measured_poiner_countはポインタが画面端に達すると正しい値が得られないことに注意。"""
        calculated_pointer_count_x, calculated_pointer_count_y = self.calc_mouse_count_to_pointer_count(
            measured_mouse_count_x, measured_mouse_count_y
        )
        print(
            f"({measured_mouse_count_x}, {measured_mouse_count_y}) -> m: ({measured_poiner_count_x:.4f}, {measured_pointer_count_y:.4f}), c: ({calculated_pointer_count_x:.4f}, {calculated_pointer_count_y:.4f}), m/c: ({0 if calculated_pointer_count_x == 0 else measured_poiner_count_x / calculated_pointer_count_x:.4f}, {0 if calculated_pointer_count_y == 0 else measured_pointer_count_y / calculated_pointer_count_y:.4f})"
        )


def calc_pointer_count_to_pointer_speed(
    pointer_count_x: float, pointer_count_y: float, mouse_count_x: float, mouse_count_y
) -> float:
    """斜め方向の補正をするためにmouse_countが必要。pointer_count_x:pointer_count_y = mouse_count_x:mouse_count_y であるべきだが、異なっている場合は平均を取る（実測値から入力値を決定したとき、量子化誤差で比が一致しないことがあるため。）"""
    scale = ((pointer_count_x / mouse_count_x) + (pointer_count_y / mouse_count_y)) / 2
    pointer_count = scale * mouse_count_norm(mouse_count_x, mouse_count_y)
    return (pointer_count / coefficient) * 150 / screen_dpi


def show_curves(
    curves: Iterable[SmoothMouseCurve],
    x_lim: float | None = 1,
    y_lim: float | None = 25,
    additional_points_of_counts=(
        (1, 0),
        (1, 1),
        (2, 0),
        (2, 1),
        (3, 0),
        (2, 2),
        (3, 1),
        (3, 2),
        (3, 3),
        (4, 0),
        (4, 1),
    ),
):
    fig, ax = plt.subplots()
    for i, curve in enumerate(curves):
        ax.plot(curve.x, curve.y, "o-", label=f"{i}")
        ax.plot(
            *zip(
                *(
                    (speed, curve.calc_applied_speed(speed))
                    for speed in (calc_mouse_speed(*point) for point in additional_points_of_counts)
                )
            ),
            ".r",
        )

    if x_lim is None:
        x_lim = max(curve.x[3] for curve in curves) * 1.3
    if y_lim is None:
        y_lim = max(curve.y[3] for curve in curves) * 1.3
    ax.set_xlim(left=0, right=x_lim)
    ax.set_ylim(bottom=0, top=y_lim)
    ax.legend()
    plt.show()


def my_round(x):
    floor_x = math.floor(x)
    if x - floor_x < 0.5:
        return floor_x
    else:
        return floor_x + 1


def fixed_point_1616_to_float(x: int) -> float:
    return x / 0x10000


def float_to_fixed_point_1616(x: float) -> int:
    return my_round(x * 0x10000)


def float_to_1616_hex_big_endian_strs(x: float) -> list[str]:
    hex_str = f"{float_to_fixed_point_1616(x):08x}"
    return list(reversed(["".join(byte_chars) for byte_chars in itertools.batched(hex_str, 2)]))


def float_to_8bytes_reg_str(x: float) -> str:
    return ",".join(float_to_1616_hex_big_endian_strs(x) + ["00"] * 4)


def reg_str_to_float(x: str):
    return fixed_point_1616_to_float(int("".join(reversed(x[:11].split(","))), 16))


def write_reg_file(smooth_mouse_curve: SmoothMouseCurve, output_filepath):
    x = smooth_mouse_curve.x
    y = smooth_mouse_curve.y
    with open(output_filepath, mode="w", encoding="utf-16") as f:
        print(
            "Windows Registry Editor Version 5.00",
            "",
            r"[HKEY_CURRENT_USER\Control Panel\Mouse]",
            '"SmoothMouseXCurve"=hex:\\',
            float_to_8bytes_reg_str(x[0]) + ",\\",
            float_to_8bytes_reg_str(x[1]) + ",\\",
            float_to_8bytes_reg_str(x[2]) + ",\\",
            float_to_8bytes_reg_str(x[3]) + ",\\",
            float_to_8bytes_reg_str(x[4]),
            '"SmoothMouseYCurve"=hex:\\',
            float_to_8bytes_reg_str(y[0]) + ",\\",
            float_to_8bytes_reg_str(y[1]) + ",\\",
            float_to_8bytes_reg_str(y[2]) + ",\\",
            float_to_8bytes_reg_str(y[3]) + ",\\",
            float_to_8bytes_reg_str(y[4]),
            file=f,
            sep="\n",
        )


def read_reg_file(reg_filepath) -> SmoothMouseCurve:
    x = []
    y = []
    with open(reg_filepath, encoding="utf-16") as f:
        for line in f:
            if line.startswith('"SmoothMouseXCurve"'):
                for _ in range(5):
                    x.append(reg_str_to_float(next(f).strip()))
            elif line.startswith('"SmoothMouseYCurve"'):
                for _ in range(5):
                    y.append(reg_str_to_float(next(f).strip()))
    return SmoothMouseCurve(x, y)


def print_mouse_speeds():
    print_mouse_speed(1, 0)
    print_mouse_speed(1, 1)
    print_mouse_speed(2, 0)
    print_mouse_speed(2, 1)
    print_mouse_speed(2, 2)
    print_mouse_speed(3, 0)
    print_mouse_speed(3, 1)
    print_mouse_speed(3, 2)
    print_mouse_speed(4, 0)
    print_mouse_speed(4, 1)
    print_mouse_speed(3, 3)
    print_mouse_speed(4, 2)
    print_mouse_speed(4, 3)


def mouse_count_norm(x: float, y: float) -> float:
    large, small = (x, y) if y == 0 or x > y else (y, x)
    # 0 <= y <= x のとき (x^2 + y^2)^(1/2) = ((1 + y^2/x^2)*x^2)^(1/2) = ( (1 + y^2/x^2)^(1/2) * x )
    # 0 <= y/x <= 1 よりこれを ((2^(1/2) - 1) * (y/x) + 1) * x に近似する。2^(1/2) - 1 を 1/2 に近似する。
    return large + 1 / 2 * small


def calc_mouse_speed(mouse_count_x: float, mouse_count_y: float) -> float:
    return mouse_count_norm(mouse_count_x, mouse_count_y) / 3.5


def print_mouse_speed(mouse_count_x, mouse_count_y):
    print(f"({mouse_count_x}, {mouse_count_y}): {calc_mouse_speed(mouse_count_x, mouse_count_y)}")


def speed_test_curve(
    target_count_x: int | None = None, target_cuont_y: int | None = None, target_speed: float | None = None, step=0.001
) -> tuple[SmoothMouseCurve, SmoothMouseCurve, SmoothMouseCurve]:
    """target_speedがNoneのとき、target_cuont_x, target_count_yから計算されるマウス速度に対して、target_speedがNoneでないならtarget_speedに対して、その周辺で値が大きく変化するSmoothMouseCurveを返す。
    :return tuple[SmoothMouseCurve, SmoothMouseCurve, SmoothMouseCurve] (curve_fast_at_target, curve_slow_at_target, curve_rise_at_target): curve_fast_at_targetは対象速度-0.001で加速する。curve_slow_at_targetは対象速度+0.001で加速する。curve_rise_at_targetは対象速度で加速する。

    count (1, 1), 理論speed 0.404061, 0.421 < 実測speed < 0.431
    count (2, 0), 理論speed 0.571428, 0.5719 < 実測speed < 0.5724
    count (2, 1), 理論speed 0.638876, 0.711 < 実測speed < 0.726
    count (2, 2), 理論speed 0.808122, 0.85 < 実測speed < 0.86

    (1, 0), (2, 0), (3, 0)について+-0.001に収まっていることを確認した
    """
    if target_speed is None and target_count_x is not None and target_cuont_y is not None:
        target_speed_ = calc_mouse_speed(target_count_x, target_cuont_y)
    elif target_speed is not None:
        target_speed_ = target_speed
    else:
        raise Exception("invalid arguments")
    low_gradient = 2.5  # デフォルトカーブ内の最も低い傾きに近い値
    steep_step = 0.0001
    temp = step + steep_step
    gradients = [low_gradient, 500 / steep_step, low_gradient, low_gradient]  # 傾きのある区間にyが500上昇する。
    fast_at_target_x = [target_speed_ - temp, target_speed_ - step, target_speed_ + 1]
    curve_fast_at_target = SmoothMouseCurve.from_gradients_and_x(gradients, fast_at_target_x)
    slow_at_target_x = [target_speed_ + step, target_speed_ + temp, target_speed_ + 1]
    curve_slow_at_target = SmoothMouseCurve.from_gradients_and_x(gradients, slow_at_target_x)
    rise_at_target_x = [target_speed_, target_speed_ + steep_step, target_speed_ + 1]
    curve_rise_at_target = SmoothMouseCurve.from_gradients_and_x(gradients, rise_at_target_x)
    return curve_fast_at_target, curve_slow_at_target, curve_rise_at_target


def make_curve_from_mouse_and_pointer_counts(
    mouse_and_pointer_counts: Sequence[tuple[tuple[float, float], tuple[float, float]]],
    remaining_gradients_and_x: tuple[Sequence[float], Sequence[float]] | None = None,
    margins: Sequence[float] = (0.01, 0.01, 0.01),
) -> SmoothMouseCurve:
    mouse_speed_and_pointer_speed_list = [
        (calc_mouse_speed(*m_p_count[0]), calc_pointer_count_to_pointer_speed(*m_p_count[1], *m_p_count[0]))
        for m_p_count in mouse_and_pointer_counts
    ]
    three_x = [
        mouse_speed_pointer_speed[0] + margin
        for mouse_speed_pointer_speed, margin in zip(mouse_speed_and_pointer_speed_list[:3], margins)
    ]
    if remaining_gradients_and_x is not None:
        three_x = [*three_x, *remaining_gradients_and_x[1]]
        return SmoothMouseCurve.from_points_and_x(
            mouse_speed_and_pointer_speed_list, three_x, remaining_gradients_and_x[0]
        )
    else:
        return SmoothMouseCurve.from_points_and_x(mouse_speed_and_pointer_speed_list, three_x)


def main():
    # MouseMovementRecorderで変更したい入力countと目標のcountを考える。
    # make_curve_from_mouse_and_pointer_counts()で入力countと目標countからcurveを作る。make_curve_from_mouse_and_pointer_counts()内のthree_xの座標を調整してよい。
    # トラックポイントにおいて
    # (1, 0) - (1, 1): 近距離の操作速度に影響する。早いと近距離がはやく軽くなるがドット飛びが大きすぎて目に余るようになる
    # (2, 0) - (3,0): 中距離の操作速度に影響する。ある程度距離が離れたものを狙うときここの速度を使っている。ここがある程度早くないと如実に遅いと感じる。しかし(1,0)-(1,1)と違いすぎると(1,1)を微妙に超えたときに飛びすぎて困ったりする。
    # (3, 1) - : 画面横半分以上を移動するような遠距離の操作速度に影響する。これもある程度大きい必要がある。
    # 途中で傾きが減るようなのも試したが、途中から重くなるような変な感覚になる。
    # ある区間の傾きを変えたとき、その区間の移動ドットの変動量が、それ以降のすべての区間にも影響することに注意。
    # この変動量の最終的な出力への影響は、「それ以降のすべての区間」の速度に達している**時間**×変動量 になる。感覚的にはには大きな操作に対してより大きな影響が出る。
    # 逆に傾きを変えた区間そのものに一瞬入るような場合にはそんなに影響はない？
    print_mouse_speeds()
    filepath = r"smooth_mouse_default.reg"
    curve = read_reg_file(filepath)
    curve2 = SmoothMouseCurve(curve.x, [y * 2 for y in curve.y])
    grad_2, x_2 = curve2.get_gradients_and_x()
    grad_5 = [grad_2[0] * 2] + [grad_2[3] * 5] * 3
    x_5 = [0.3] + [x / 2 for x in x_2[1:]]
    curve5 = SmoothMouseCurve.from_gradients_and_x(grad_5, x_5)
    grad_6 = [grad_2[0] * 1.5, grad_2[1] * 1.5] + [grad_2[3] * 2] * 2
    curve6 = SmoothMouseCurve.from_gradients_and_x(grad_6, [0.3, 0.4, 1])
    grad_7 = [grad_2[0] * 1.5, grad_2[1] * 1.5] + [grad_2[3] * 2, grad_2[3] * 4]
    curve7 = SmoothMouseCurve.from_gradients_and_x(grad_7, [0.3, 0.4, 0.9])
    curve8 = make_curve_from_mouse_and_pointer_counts([((1, 1), (9.5, 9.5))], ([grad_2[3] * 6] * 3, [0.9, 1.0]))
    curve9 = make_curve_from_mouse_and_pointer_counts(
        [((1, 1), (9.5, 9.5))], ([grad_2[3] * 6, grad_2[3] * 4, grad_2[3] * 4], [0.86, 1.0])
    )
    curve10 = make_curve_from_mouse_and_pointer_counts(
        [((1, 1), (7, 7))], ([grad_2[3] * 4.5, grad_2[3] * 5, grad_2[3] * 5], [0.86, 1.0])
    )
    c_10_speed_3 = SmoothMouseCurve(curve10.x, [y * 0.4 for y in curve10.y])

    # 6.5625は((1,1), (3,3)) の傾き。6.5625 * 16はgrad_2[3] * 4より大きい
    curve11 = make_curve_from_mouse_and_pointer_counts(
        [((1, 1), (3, 3))], ([6.5625 * 4, 6.5625 * 8, 6.5625 * 8], [0.86, 1.29])
    )

    curve12 = make_curve_from_mouse_and_pointer_counts(
        [((1, 1), (4, 4))], ([8.75 * 6, 8.75 * 10, 8.75 * 12], [0.86, 1.29])
    )

    s = lambda x, y: calc_mouse_speed(x, y) + 0.01  # これまでのcurveはこのような値を直接書いていた
    curve13 = make_curve_from_mouse_and_pointer_counts(
        [((1, 1), (4, 4))], ([8.75 * 6, 8.75 * 6, 8.75 * 12], [s(2, 2), s(3, 3)])
    )

    curve14 = make_curve_from_mouse_and_pointer_counts(
        [((1, 1), (4, 4))], ([8.75 * 6, 8.75 * 6, 8.75 * 10], [s(2, 2), s(3, 3)])
    )

    curve15 = make_curve_from_mouse_and_pointer_counts(
        [((1, 1), (4.5, 4.5))], ([8.75 * 6, 8.75 * 6, 8.75 * 10], [s(2, 2), s(3, 3)])
    )  # current speed

    output_reg_filepath = r"smooth_mouse.reg"
    write_reg_file(curve15, output_reg_filepath)

    show_curves([curve2, curve10, c_10_speed_3, curve11, curve12, curve13, curve14, curve15], x_lim=2, y_lim=100)

    # 以下のコードは必ず残しておく
    # はずれ値はコメントアウトしておいた。はずれ値の原因は不明。低速度では量子化誤差が非常に大きくなるので注意。
    # data = [
    #     ((1, 0), (3, 0)),
    #     ((1, 0), (4, 0)),
    #     ((1, 1), (5, 5)),
    #     ((1, 1), (4, 4)),
    #     # ((2, 0), (12, 0)),
    #     # ((2, 0), (13, 0)),
    #     ((2, 0), (19, 0)),
    #     ((2, 0), (18, 0)),
    #     # ((2, 1), (16, 7)),
    #     # ((2, 1), (15, 7)),
    #     # ((2, 1), (15, 8)),
    #     ((2, 1), (23, 12)),
    #     ((2, 1), (23, 11)),
    #     ((3, 0), (40, 0)),
    #     ((3, 0), (39, 0)),

    #     ((4, 0), (79, 0)),
    #     ((4, 0), (80, 0)),
    #     ((4, 1), (77, 19)),
    #     ((4, 1), (90, 23)),
    #     ((4, 1), (98, 49)),
    #     ((4, 2), (98, 49)),
    #     ((5, 0), (123, 0)),
    #     ((5, 1), (138, 27)),
    #     ((5, 2), (138, 56)),
    #     ((5, 3), (144, 87)),
    #     ((7, 3), (225, 97)),
    #     ((7, 3), (225, 96)),
    #     ((6, 3), (184, 92)),
    #     ((7, 1), (214, 30)),
    #     ((7, 0), (209, 0)),
    #     ((8, 0), (251, 0)),
    #     ((10, 0), (338, 0)),
    #     ((12, 0), (424, 0)),
    #     ((12, 0), (423, 0)),
    #     ((15, 8), (572, 305)),
    #     ((15, 9), (573, 344)),
    #     ((13, 8), (488, 300)),
    #     ((12, 8), (447, 298)),
    #     ((13, 7), (486, 262))
    # ]
    # for mouse, pointer in data:
    #     curve7.print_measured_count_analysis(*mouse, *pointer)


if __name__ == "__main__":
    main()
