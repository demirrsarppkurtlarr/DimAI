"""Pseudo-3D / game generators used by DimAI codegen."""
from __future__ import annotations


def gen_3d_ascii(_: str = "") -> tuple[str, str, str]:
    code = (
        '"""Pseudo-3D koridor oyunu — stdlib raycasting (pygame yok).\n'
        "\n"
        "Mimari: map | camera | renderer | input loop\n"
        '"""\n'
        "from __future__ import annotations\n"
        "\n"
        "import math\n"
        "import os\n"
        "\n"
        "\n"
        "MAP = [\n"
        '    "############",\n'
        '    "#..........#",\n'
        '    "#..##......#",\n'
        '    "#..........#",\n'
        '    "#....##....#",\n'
        '    "#..........#",\n'
        '    "############",\n'
        "]\n"
        "W, H = len(MAP[0]), len(MAP)\n"
        "FOV = math.pi / 3\n"
        "DEPTH = 12.0\n"
        "\n"
        "\n"
        "class Camera:\n"
        "    def __init__(self) -> None:\n"
        "        self.x = 3.5\n"
        "        self.y = 3.5\n"
        "        self.a = 0.0\n"
        "\n"
        "\n"
        "def hit_wall(x: float, y: float) -> bool:\n"
        "    ix, iy = int(x), int(y)\n"
        "    if ix < 0 or iy < 0 or ix >= W or iy >= H:\n"
        "        return True\n"
        '    return MAP[iy][ix] == "#"\n'
        "\n"
        "\n"
        "def render(cam: Camera, cols: int = 60, rows: int = 22) -> str:\n"
        "    lines: list[str] = []\n"
        "    for y in range(rows):\n"
        "        row: list[str] = []\n"
        "        for x in range(cols):\n"
        "            ray = (cam.a - FOV / 2.0) + (x / cols) * FOV\n"
        "            dist = 0.0\n"
        "            hit = False\n"
        "            step = 0.08\n"
        "            while dist < DEPTH and not hit:\n"
        "                dist += step\n"
        "                rx = cam.x + math.cos(ray) * dist\n"
        "                ry = cam.y + math.sin(ray) * dist\n"
        "                if hit_wall(rx, ry):\n"
        "                    hit = True\n"
        "            ceiling = int(rows / 2.0 - rows / (dist + 0.1))\n"
        "            floor = rows - ceiling\n"
        "            if y < ceiling:\n"
        '                shade = " "\n'
        "            elif y > floor:\n"
        '                shade = "."\n'
        "            else:\n"
        "                if dist < DEPTH / 4:\n"
        '                    shade = "#"\n'
        "                elif dist < DEPTH / 3:\n"
        '                    shade = "X"\n'
        "                elif dist < DEPTH / 2:\n"
        '                    shade = "x"\n'
        "                else:\n"
        '                    shade = "-"\n'
        "            row.append(shade)\n"
        '        lines.append("".join(row))\n'
        '    return "\\n".join(lines)\n'
        "\n"
        "\n"
        "def main() -> None:\n"
        "    cam = Camera()\n"
        '    print("Pseudo-3D koridor. Komutlar: w a s d | q=cikis")\n'
        "    while True:\n"
        '        os.system("cls" if os.name == "nt" else "clear")\n'
        "        print(render(cam))\n"
        '        print(f"pos=({cam.x:.1f},{cam.y:.1f}) ang={cam.a:.2f}")\n'
        '        cmd = input("> ").strip().lower()\n'
        '        if cmd in {"q", "quit", "cikis"}:\n'
        "            break\n"
        "        step, turn = 0.35, 0.28\n"
        "        nx, ny = cam.x, cam.y\n"
        '        if "w" in cmd:\n'
        "            nx += math.cos(cam.a) * step\n"
        "            ny += math.sin(cam.a) * step\n"
        '        if "s" in cmd:\n'
        "            nx -= math.cos(cam.a) * step\n"
        "            ny -= math.sin(cam.a) * step\n"
        '        if "a" in cmd:\n'
        "            cam.a -= turn\n"
        '        if "d" in cmd:\n'
        "            cam.a += turn\n"
        "        if not hit_wall(nx, ny):\n"
        "            cam.x, cam.y = nx, ny\n"
        "\n"
        "\n"
        'if __name__ == "__main__":\n'
        "    main()\n"
    )
    return "Pseudo-3D koridor oyunu (raycasting, stdlib):", code, "python"
