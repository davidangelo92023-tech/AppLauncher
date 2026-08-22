import os
import sys
import json
import math
import random
import threading
import datetime

import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox

# ---------------- shared helpers ----------------

BG = "#07050f"
CARD = "#150f28"
CARD2 = "#221a3d"
TEXT = "#eaf2ff"
MUTED = "#8f87c2"
ACC = "#00f0ff"
GREEN = "#39ff8c"
RED = "#ff2255"

ACCENTS = ["#00f0ff", "#ff2bd6", "#39ff8c", "#ffb86c", "#9d7bff", "#ff2255", "#4fd6d6", "#ffe066"]

SCORES_FILE = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AppLauncher", "games.json")


def _load_scores():
    try:
        with open(SCORES_FILE, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_scores(data):
    try:
        os.makedirs(os.path.dirname(SCORES_FILE), exist_ok=True)
        with open(SCORES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _header(win, parent, title, subtitle=""):
    bar = tk.Frame(win, bg=BG)
    bar.pack(fill="x", padx=14, pady=(10, 4))
    tk.Label(bar, text=title, font=tkfont.Font(family="Segoe UI", size=14, weight="bold"),
             bg=BG, fg=TEXT).pack(side="left")
    if subtitle:
        tk.Label(bar, text="   " + subtitle, font=("Segoe UI", 8), bg=BG,
                 fg=MUTED).pack(side="left", anchor="s", pady=(0, 4))


def _btn(parent, text, cmd, color=ACC, fg="#0d1220"):
    return tk.Button(parent, text=text, command=cmd, bg=color, fg=fg,
                     activebackground=color, activeforeground=fg, relief="flat", bd=0,
                     padx=14, pady=5, font=("Segoe UI", 9, "bold"), cursor="hand2")


def _btn2(parent, text, cmd):
    return tk.Button(parent, text=text, command=cmd, bg=CARD2, fg=TEXT,
                     activebackground="#2c1f52", activeforeground="#ffffff",
                     relief="flat", bd=0, padx=12, pady=5, font=("Segoe UI", 9), cursor="hand2")


class GamesWindow(tk.Toplevel):
    def __init__(self, app=None):
        super().__init__(app)
        self.title("Games")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.geometry("760x610")
        _header(self, self, "Games", "pick a game to play")

        games = [
            ("\u265F  Chess", "Full chess vs an AI", ChessWindow),
            ("Tic-Tac-Toe", "Beat the unbeatable AI", TicTacToeWindow),
            ("Connect 4", "Get four in a row", Connect4Window),
            ("Snake", "Grow and dodge walls", SnakeWindow),
            ("2048", "Merge the tiles", Tile2048Window),
            ("Wordle", "Guess the word in 6", WordleWindow),
            ("Memory", "Match all the pairs", MemoryWindow),
            ("Pong", "Beat the AI to 7 points", PongWindow),
            ("Minesweeper", "Clear the board, avoid the mines", MinesweeperWindow),
        ]
        grid = tk.Frame(self, bg=BG)
        grid.pack(fill="both", expand=True, padx=16, pady=12)
        for i, (name, desc, cls) in enumerate(games):
            color = ACCENTS[i % len(ACCENTS)]
            cell = tk.Frame(grid, bg=CARD)
            cell.grid(row=i // 2, column=i % 2, padx=8, pady=8, sticky="nsew")
            for c in range(2):
                grid.columnconfigure(c, weight=1)
            tk.Button(cell, text=name, command=lambda c=cls: c(self),
                      bg=color, fg="#0d1220", activebackground=color,
                      activeforeground="#0d1220", relief="flat", bd=0,
                      font=("Segoe UI", 11, "bold"), pady=8, cursor="hand2"
                      ).pack(fill="x", padx=8, pady=(8, 2))
            tk.Label(cell, text=desc, font=("Segoe UI", 8), bg=CARD, fg=MUTED).pack(padx=8, pady=(0, 8))

# ---------------- Pong ----------------

class PongWindow(tk.Toplevel):
    W, H = 560, 360
    PW, PH = 10, 70
    WIN_SCORE = 7

    def __init__(self, app=None):
        super().__init__(app)
        self.title("Pong")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.best = _load_scores().get("pong", 0)
        self._reset()

        _header(self, self, "Pong", "first to 7 \u2014 move your mouse")
        self.score_lbl = tk.Label(self, text="You 0  \u2014  AI 0   Best 0",
                                  font=("Segoe UI", 10, "bold"), bg=BG, fg=TEXT)
        self.score_lbl.pack()
        self.cv = tk.Canvas(self, width=self.W, height=self.H, bg="#0a0714", highlightthickness=0)
        self.cv.pack(padx=16, pady=8)
        self.cv.bind("<Motion>", self._mouse)
        self.cv.bind("<B1-Motion>", self._mouse)
        self.bind("<KeyPress>", self._key)
        self.focus_set()
        self._serve()
        self._tick()

    def _reset(self):
        self.py = self.H / 2 - self.PH / 2
        self.ay = self.H / 2 - self.PH / 2
        self.pscore = 0
        self.ascore = 0
        self.gameover = False
        self.speed = 4.8

    def _serve(self):
        self.bx, self.by = self.W / 2, self.H / 2
        self.bdx = 1 if random.random() < 0.5 else -1
        self.bdy = math.tan(random.uniform(-0.55, 0.55))

    def _mouse(self, e):
        if self.gameover:
            return
        self.py = min(max(0, e.y - self.PH / 2), self.H - self.PH)
        self._draw()

    def _key(self, e):
        if e.keysym in ("r", "R"):
            self._reset()
            self._serve()
            self._draw()
            return
        if self.gameover:
            return
        if e.keysym in ("Up", "w", "W"):
            self.py = max(0, self.py - 22)
        elif e.keysym in ("Down", "s", "S"):
            self.py = min(self.H - self.PH, self.py + 22)
        self._draw()

    def _step(self):
        self.bx += self.bdx * self.speed
        self.by += self.bdy * self.speed
        if self.by <= 0:
            self.by = 0
            self.bdy = abs(self.bdy)
        elif self.by >= self.H:
            self.by = self.H
            self.bdy = -abs(self.bdy)

        if self.bdx > 0:
            target = self.by - self.PH / 2
            if self.ay < target - 2:
                self.ay = min(self.H - self.PH, self.ay + 4.2)
            elif self.ay > target + 2:
                self.ay = max(0, self.ay - 4.2)
        else:
            mid = self.H / 2 - self.PH / 2
            if self.ay < mid - 2:
                self.ay = min(self.H - self.PH, self.ay + 2.0)
            elif self.ay > mid + 2:
                self.ay = max(0, self.ay - 2.0)

        if self.bdx < 0:
            if self.bx <= 20 + self.PW:
                if self.py <= self.by <= self.py + self.PH:
                    self.bx = 20 + self.PW
                    self._bounce(self.py)
                elif self.bx < 0:
                    self._score("ai")
                    return
        elif self.bx >= self.W - 20 - self.PW:
            if self.ay <= self.by <= self.ay + self.PH:
                self.bx = self.W - 20 - self.PW
                self._bounce(self.ay)
            elif self.bx > self.W:
                self._score("player")
                return

    def _bounce(self, paddle_top):
        rel = (self.by - paddle_top) / self.PH - 0.5
        self.bdx = -self.bdx * 1.05
        self.bdy = rel * 1.6
        self.speed = min(11.0, self.speed + 0.35)

    def _score(self, who):
        if who == "player":
            self.pscore += 1
        else:
            self.ascore += 1
        if self.pscore >= self.WIN_SCORE or self.ascore >= self.WIN_SCORE:
            self.gameover = True
            if self.pscore > self.best:
                self.best = self.pscore
                data = _load_scores()
                data["pong"] = self.best
                _save_scores(data)
        else:
            self._serve()

    def _tick(self):
        if not self.gameover:
            self._step()
        self._draw()
        self.after(16, self._tick)

    def _draw(self):
        c = self.cv
        c.delete("all")
        c.create_rectangle(20, self.py, 20 + self.PW, self.py + self.PH,
                           fill="#00f0ff", outline="")
        c.create_rectangle(self.W - 20 - self.PW, self.ay, self.W - 20, self.ay + self.PH,
                           fill="#ff2255", outline="")
        for y in range(10, self.H, 26):
            c.create_rectangle(self.W / 2 - 2, y, self.W / 2 + 2, y + 12, fill=MUTED, outline="")
        c.create_oval(self.bx - 7, self.by - 7, self.bx + 7, self.by + 7,
                      fill="#eaf2ff", outline="")
        self.score_lbl.config(text=f"You {self.pscore}  \u2014  AI {self.ascore}   Best {max(self.best, self.pscore)}")
        if self.gameover:
            win = self.pscore > self.ascore
            c.create_text(self.W // 2, self.H // 2 - 18, text="YOU WIN!" if win else "AI WINS",
                          fill=GREEN if win else RED,
                          font=tkfont.Font(family="Segoe UI", size=30, weight="bold"))
            c.create_text(self.W // 2, self.H // 2 + 22,
                          text="press R to restart", fill=TEXT, font=("Segoe UI", 12))


# ---------------- Chess ----------------

class Chess:
    VAL = {"P": 100, "N": 320, "B": 330, "R": 500, "Q": 900, "K": 0}
    INF = 10 ** 9
    PST = {
        "P": [0,0,0,0,0,0,0,0, 50,50,50,50,50,50,50,50, 10,10,20,30,30,20,10,10,
              5,5,10,25,25,10,5,5, 0,0,0,20,20,0,0,0, 5,-5,-10,0,0,-10,-5,5,
              5,10,10,-20,-20,10,10,5, 0,0,0,0,0,0,0,0],
        "N": [-50,-40,-30,-30,-30,-30,-40,-50, -40,-20,0,0,0,0,-20,-40, -30,0,10,15,15,10,0,-30,
              -30,5,15,20,20,15,5,-30, -30,0,15,20,20,15,0,-30, -30,5,10,15,15,10,5,-30,
              -40,-20,0,5,5,0,-20,-40, -50,-40,-30,-30,-30,-30,-40,-50],
        "B": [-20,-10,-10,-10,-10,-10,-10,-20, -10,0,0,0,0,0,0,-10, -10,0,5,10,10,5,0,-10,
              -10,5,5,10,10,5,5,-10, -10,0,10,10,10,10,0,-10, -10,10,10,10,10,10,10,-10,
              -10,5,0,0,0,0,5,-10, -20,-10,-10,-10,-10,-10,-10,-20],
        "R": [0,0,0,0,0,0,0,0, 5,10,10,10,10,10,10,5, -5,0,0,0,0,0,0,-5,
              -5,0,0,0,0,0,0,-5, -5,0,0,0,0,0,0,-5, -5,0,0,0,0,0,0,-5,
              -5,0,0,0,0,0,0,-5, 0,0,0,5,5,0,0,0],
        "Q": [-20,-10,-10,-5,-5,-10,-10,-20, -10,0,0,0,0,0,0,-10, -10,0,5,5,5,5,0,-10,
              -5,0,5,5,5,5,0,-5, 0,0,5,5,5,5,0,-5, -10,5,5,5,5,5,0,-10,
              -10,0,5,0,0,0,0,-10, -20,-10,-10,-5,-5,-10,-10,-20],
        "K": [-30,-40,-40,-50,-50,-40,-40,-30, -30,-40,-40,-50,-50,-40,-40,-30,
              -30,-40,-40,-50,-50,-40,-40,-30, -30,-40,-40,-50,-50,-40,-40,-30,
              -20,-30,-30,-40,-40,-30,-30,-20, -10,-20,-20,-20,-20,-20,-20,-10,
              20,20,0,0,0,0,20,20, 20,30,10,0,0,10,30,20],
    }

    def __init__(self):
        self.reset()

    def reset(self):
        b = [[None] * 8 for _ in range(8)]
        back = "RNBQKBNR"
        for c in range(8):
            b[0][c] = "b" + back[c]
            b[1][c] = "bP"
            b[6][c] = "wP"
            b[7][c] = "w" + back[c]
        self.board = b
        self.turn = "w"
        self.castle = {"w": {"K": True, "Q": True}, "b": {"K": True, "Q": True}}
        self.ep = None
        self.stack = []

    def _inb(self, r, c):
        return 0 <= r < 8 and 0 <= c < 8

    def king(self, color):
        for r in range(8):
            for c in range(8):
                if self.board[r][c] == color + "K":
                    return (r, c)
        return None

    def attacks(self, src, dst, pt):
        sr, sc = src
        tr, tc = dst
        if pt == "P":
            d = -1 if self.board[sr][sc][0] == "w" else 1
            return tr == sr + d and abs(tc - sc) == 1
        if pt == "N":
            return (abs(tr - sr), abs(tc - sc)) in ((1, 2), (2, 1))
        if pt == "K":
            return max(abs(tr - sr), abs(tc - sc)) == 1
        if pt in ("B", "Q") and abs(tr - sr) == abs(tc - sc) and tr != sr:
            return self._clear(sr, sc, tr, tc, 1 if tr > sr else -1, 1 if tc > sc else -1)
        if pt in ("R", "Q"):
            if tr == sr and tc != sc:
                return self._clear(sr, sc, tr, tc, 0, 1 if tc > sc else -1)
            if tc == sc and tr != sr:
                return self._clear(sr, sc, tr, tc, 1 if tr > sr else -1, 0)
        return False

    def _clear(self, sr, sc, tr, tc, dr, dc):
        r, c = sr + dr, sc + dc
        while (r, c) != (tr, tc):
            if self.board[r][c]:
                return False
            r += dr
            c += dc
        return True

    def attacked(self, sq, color):
        opp = "b" if color == "w" else "w"
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p and p[0] == opp and self.attacks((r, c), sq, p[1]):
                    return True
        return False

    def in_check(self, color):
        k = self.king(color)
        return k is not None and self.attacked(k, color)

    def _pawn_moves(self, r, c, color):
        moves = []
        d = -1 if color == "w" else 1
        start = 6 if color == "w" else 1
        if self._inb(r + d, c) and self.board[r + d][c] is None:
            moves.append(((r, c), (r + d, c)))
            if r == start and self.board[r + 2 * d][c] is None:
                moves.append(((r, c), (r + 2 * d, c)))
        for dc in (-1, 1):
            tc = c + dc
            if self._inb(r + d, tc):
                t = self.board[r + d][tc]
                if t and t[0] != color:
                    moves.append(((r, c), (r + d, tc)))
                elif self.ep and (r + d, tc) == self.ep:
                    moves.append(((r, c), (r + d, tc)))
        return moves

    def pseudo(self):
        color = self.turn
        moves = []
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if not p or p[0] != color:
                    continue
                pt = p[1]
                if pt == "P":
                    moves.extend(self._pawn_moves(r, c, color))
                elif pt == "N":
                    for dr, dc in ((2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)):
                        rr, cc = r + dr, c + dc
                        if self._inb(rr, cc) and (self.board[rr][cc] is None or self.board[rr][cc][0] != color):
                            moves.append(((r, c), (rr, cc)))
                elif pt == "K":
                    for dr in (-1, 0, 1):
                        for dc in (-1, 0, 1):
                            if dr == 0 and dc == 0:
                                continue
                            rr, cc = r + dr, c + dc
                            if self._inb(rr, cc) and (self.board[rr][cc] is None or self.board[rr][cc][0] != color):
                                moves.append(((r, c), (rr, cc)))
                    self._castle_moves(r, c, color, moves)
                else:
                    dirs = {"B": ((-1, -1), (-1, 1), (1, -1), (1, 1)),
                            "R": ((-1, 0), (1, 0), (0, -1), (0, 1)),
                            "Q": ((-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1))}[pt]
                    for dr, dc in dirs:
                        rr, cc = r + dr, c + dc
                        while self._inb(rr, cc):
                            t = self.board[rr][cc]
                            if t is None:
                                moves.append(((r, c), (rr, cc)))
                            else:
                                if t[0] != color:
                                    moves.append(((r, c), (rr, cc)))
                                break
                            rr += dr
                            cc += dc
        return moves

    def _castle_moves(self, r, c, color, moves):
        if self.in_check(color):
            return
        if self.castle[color]["K"] and self.board[r][5] is None and self.board[r][6] is None \
                and self.board[r][7] == color + "R":
            if not self.attacked((r, 5), color) and not self.attacked((r, 6), color):
                moves.append(((r, c), (r, 6)))
        if self.castle[color]["Q"] and self.board[r][3] is None and self.board[r][2] is None \
                and self.board[r][1] is None and self.board[r][0] == color + "R":
            if not self.attacked((r, 3), color) and not self.attacked((r, 2), color):
                moves.append(((r, c), (r, 2)))

    def legal(self):
        res = []
        for m in self.pseudo():
            self.apply(m)
            if not self.in_check(self.turn):
                res.append(m)
            self.unmake()
        return res

    def apply(self, move):
        (sr, sc), (tr, tc) = move
        p = self.board[sr][sc]
        captured = self.board[tr][tc]
        promo = p[1] == "P" and tr in (0, 7)
        new_p = p[0] + "Q" if promo else p
        ep = self.ep
        castle = {col: dict(v) for col, v in self.castle.items()}
        self.stack.append((move, p, captured, ep, castle))
        self.board[tr][tc] = new_p
        self.board[sr][sc] = None
        if p[1] == "P" and abs(tr - sr) == 2:
            self.ep = ((sr + tr) // 2, sc)
        else:
            self.ep = None
        if p[1] == "P" and tc != sc and captured is None:
            self.board[sr][tc] = None
        if p[1] == "K":
            if tc - sc == 2:
                self.board[tr][5] = self.board[tr][7]
                self.board[tr][7] = None
            elif tc - sc == -2:
                self.board[tr][3] = self.board[tr][0]
                self.board[tr][0] = None
            self.castle[p[0]] = {"K": False, "Q": False}
        if p[1] == "R":
            if sc == 0:
                self.castle[p[0]]["Q"] = False
            if sc == 7:
                self.castle[p[0]]["K"] = False
        if captured and captured[1] == "R":
            if (tr, tc) == (0, 0):
                self.castle["b"]["Q"] = False
            elif (tr, tc) == (0, 7):
                self.castle["b"]["K"] = False
            elif (tr, tc) == (7, 0):
                self.castle["w"]["Q"] = False
            elif (tr, tc) == (7, 7):
                self.castle["w"]["K"] = False
        self.turn = "b" if self.turn == "w" else "w"

    def unmake(self):
        move, p, captured, ep, castle = self.stack.pop()
        (sr, sc), (tr, tc) = move
        self.board[sr][sc] = p
        self.board[tr][tc] = captured
        if p[1] == "P" and tc != sc and captured is None:
            self.board[sr][tc] = p[0] + "P"
        if p[1] == "K":
            if tc - sc == 2:
                self.board[tr][7] = self.board[tr][5]
                self.board[tr][5] = None
            elif tc - sc == -2:
                self.board[tr][0] = self.board[tr][3]
                self.board[tr][3] = None
        self.ep = ep
        self.castle = castle
        self.turn = "b" if self.turn == "w" else "w"

    def evaluate(self):
        score = 0
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if not p:
                    continue
                idx = r * 8 + c
                if p[0] == "w":
                    score += self.VAL[p[1]] + self.PST[p[1]][idx]
                else:
                    score -= self.VAL[p[1]] + self.PST[p[1]][idx]
        return score

    def _search(self, depth, alpha, beta, maximizing):
        moves = self.legal()
        if not moves:
            if self.in_check(self.turn):
                return -self.INF if maximizing else self.INF
            return 0
        if depth == 0:
            return self.evaluate()
        if maximizing:
            best = -self.INF
            for m in moves:
                self.apply(m)
                v = self._search(depth - 1, alpha, beta, False)
                self.unmake()
                if v > best:
                    best = v
                if v > alpha:
                    alpha = v
                if beta <= alpha:
                    break
            return best
        best = self.INF
        for m in moves:
            self.apply(m)
            v = self._search(depth - 1, alpha, beta, True)
            self.unmake()
            if v < best:
                best = v
            if v < beta:
                beta = v
            if beta <= alpha:
                break
        return best

    def best_move(self, depth):
        moves = self.legal()
        if not moves:
            return None
        random.shuffle(moves)

        def order(m):
            (sr, sc), (tr, tc) = m
            cap = 1 if self.board[tr][tc] else 0
            pr = 1 if self.board[sr][sc][1] == "P" and tr in (0, 7) else 0
            return -(cap * 10 + pr)

        moves.sort(key=order)
        best = None
        if self.turn == "w":
            alpha, beta = -self.INF, self.INF
            for m in moves:
                self.apply(m)
                v = self._search(depth - 1, alpha, beta, False)
                self.unmake()
                if v > alpha:
                    alpha = v
                    best = m
        else:
            alpha, beta = -self.INF, self.INF
            for m in moves:
                self.apply(m)
                v = self._search(depth - 1, alpha, beta, True)
                self.unmake()
                if v < beta:
                    beta = v
                    best = m
        return best

    def status(self):
        moves = self.legal()
        if moves:
            if self.in_check(self.turn):
                return "check"
            return "ok"
        if self.in_check(self.turn):
            return "checkmate"
        return "stalemate"


GLYPHS = {"wP": "\u2659", "wN": "\u2658", "wB": "\u2657", "wR": "\u2656", "wQ": "\u2655", "wK": "\u2654",
          "bP": "\u265F", "bN": "\u265E", "bB": "\u265D", "bR": "\u265C", "bQ": "\u265B", "bK": "\u265A"}
SQ_LIGHT = "#f0d9b5"
SQ_DARK = "#b58863"
PIECE_COLOR = "#26221c"


class ChessWindow(tk.Toplevel):
    CELL = 66
    DIFFS = {"Easy": 1, "Medium": 2, "Hard": 3}

    def __init__(self, app=None):
        super().__init__(app)
        self.title("Chess vs AI")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.engine = Chess()
        self.human = "w"
        self.flipped = False
        self.selected = None
        self.legal_moves = []
        self.last_move = None
        self.game_over = False
        self.thinking = False
        self.diff = "Medium"

        _header(self, self, "\u265F  Chess vs AI", "click a piece, then a highlighted square")
        self.status_lbl = tk.Label(self, text="Your move", font=("Segoe UI", 10, "bold"),
                                   bg=BG, fg=TEXT)
        self.status_lbl.pack(anchor="w", padx=14)

        body = tk.Frame(self, bg=BG)
        body.pack(padx=14, pady=8)
        n = 8 * self.CELL
        self.cv = tk.Canvas(body, width=n, height=n, bg=SQ_LIGHT, highlightthickness=0)
        self.cv.pack(side="left")
        self.cv.bind("<Button-1>", self._click)

        side = tk.Frame(body, bg=BG)
        side.pack(side="left", fill="y", padx=(12, 0))
        _btn2(side, "New game", self._new_game).pack(fill="x", pady=3)
        _btn2(side, "Play as Black", self._switch_sides).pack(fill="x", pady=3)
        _btn2(side, "Undo move", self._undo).pack(fill="x", pady=3)
        tk.Label(side, text="AI difficulty", font=("Segoe UI", 8), bg=BG, fg=MUTED).pack(anchor="w", pady=(12, 2))
        self.diff_var = tk.StringVar(value=self.diff)
        om = tk.OptionMenu(side, self.diff_var, *self.DIFFS.keys())
        om.config(bg=CARD2, fg=TEXT, activebackground="#2c1f52", activeforeground="#ffffff",
                  relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 9), cursor="hand2")
        om["menu"].config(bg=CARD2, fg=TEXT, activebackground="#2c1f52", bd=0)
        om.pack(fill="x")
        tk.Label(side, text="", bg=BG).pack(fill="y", expand=True)

        self._draw()
        self._update_status()

    # ---------- view ----------
    def _sq(self, r, c):
        if self.flipped:
            return 7 - r, 7 - c
        return r, c

    def _draw(self):
        c = self.cv
        c.delete("all")
        n = 8 * self.CELL
        for r in range(8):
            for col in range(8):
                dr, dc = self._sq(r, col)
                x, y = dc * self.CELL, dr * self.CELL
                fill = SQ_LIGHT if (r + col) % 2 == 0 else SQ_DARK
                c.create_rectangle(x, y, x + self.CELL, y + self.CELL, fill=fill, outline="")
        if self.last_move:
            for (lr, lc) in self.last_move:
                dr, dc = self._sq(lr, lc)
                c.create_rectangle(dc * self.CELL, dr * self.CELL, dc * self.CELL + self.CELL,
                                   dr * self.CELL + self.CELL, outline="#e5c100", width=4)
        if self.selected:
            sr, sc = self.selected
            dr, dc = self._sq(sr, sc)
            c.create_rectangle(dc * self.CELL, dr * self.CELL, dc * self.CELL + self.CELL,
                               dr * self.CELL + self.CELL, outline=ACC, width=4)
            for (tr, tc) in self.legal_moves:
                dr2, dc2 = self._sq(tr, tc)
                if self.engine.board[tr][tc]:
                    c.create_oval(dc2 * self.CELL + 4, dr2 * self.CELL + 4,
                                  dc2 * self.CELL + self.CELL - 4, dr2 * self.CELL + self.CELL - 4,
                                  outline=RED, width=3)
                else:
                    c.create_oval(dc2 * self.CELL + self.CELL // 2 - 6,
                                  dr2 * self.CELL + self.CELL // 2 - 6,
                                  dc2 * self.CELL + self.CELL // 2 + 6,
                                  dr2 * self.CELL + self.CELL // 2 + 6, fill="#000000", outline="")
        if self.engine.in_check(self.engine.turn):
            k = self.engine.king(self.engine.turn)
            if k:
                dr, dc = self._sq(*k)
                c.create_rectangle(dc * self.CELL, dr * self.CELL, dc * self.CELL + self.CELL,
                                   dr * self.CELL + self.CELL, outline=RED, width=4)
        font = tkfont.Font(family="Segoe UI Symbol", size=34)
        for r in range(8):
            for col in range(8):
                p = self.engine.board[r][col]
                if p:
                    dr, dc = self._sq(r, col)
                    c.create_text(dc * self.CELL + self.CELL // 2, dr * self.CELL + self.CELL // 2,
                                  text=GLYPHS[p], font=font, fill=PIECE_COLOR)

    def _update_status(self):
        st = self.engine.status()
        turn_name = "White" if self.engine.turn == "w" else "Black"
        who = "you" if self.engine.turn == self.human else "AI"
        if st == "check":
            self.status_lbl.config(text=f"{turn_name} is in check ({who})", fg="#ffd166")
        elif st == "checkmate":
            loser = "White" if self.engine.turn == "w" else "Black"
            winner = "Black" if self.engine.turn == "w" else "White"
            self.game_over = True
            self.status_lbl.config(text=f"Checkmate! {winner} wins", fg=GREEN)
        elif st == "stalemate":
            self.game_over = True
            self.status_lbl.config(text="Stalemate - draw", fg=MUTED)
        else:
            self.status_lbl.config(text=f"{turn_name}'s turn ({who})", fg=TEXT)

    # ---------- interaction ----------
    def _click(self, event):
        if self.thinking or self.game_over:
            return
        if self.engine.turn != self.human:
            return
        dc = event.x // self.CELL
        dr = event.y // self.CELL
        r, c = self._sq(dr, dc)
        if self.selected and (r, c) in self.legal_moves:
            self._human_move((self.selected, (r, c)))
            return
        p = self.engine.board[r][c]
        if p and p[0] == self.human:
            self.selected = (r, c)
            self.legal_moves = [m[1] for m in self.engine.legal() if m[0] == (r, c)]
        else:
            self.selected = None
            self.legal_moves = []
        self._draw()

    def _human_move(self, move):
        self.engine.apply(move)
        self.last_move = move
        self.selected = None
        self.legal_moves = []
        self._draw()
        if self.engine.status() == "checkmate" or self.engine.status() == "stalemate":
            self._update_status()
            return
        self.thinking = True
        self.status_lbl.config(text="Thinking\u2026", fg=MUTED)
        threading.Thread(target=self._ai_worker, daemon=True).start()

    def _ai_worker(self):
        depth = self.DIFFS[self.diff_var.get()]
        move = self.engine.best_move(depth)
        try:
            if self.winfo_exists():
                self.after(0, lambda: self._apply_ai(move))
        except Exception:
            pass

    def _apply_ai(self, move):
        self.thinking = False
        if move:
            self.engine.apply(move)
            self.last_move = move
        self._draw()
        self._update_status()

    def _new_game(self):
        self.engine = Chess()
        self.human = "w"
        self.flipped = False
        self.selected = None
        self.legal_moves = []
        self.last_move = None
        self.game_over = False
        self._draw()
        self._update_status()

    def _switch_sides(self):
        self.human = "b" if self.human == "w" else "w"
        self.flipped = not self.flipped
        self.selected = None
        self.legal_moves = []
        self._draw()
        if self.engine.turn != self.human and not self.thinking and not self.game_over:
            self.thinking = True
            self.status_lbl.config(text="Thinking\u2026", fg=MUTED)
            threading.Thread(target=self._ai_worker, daemon=True).start()

    def _undo(self):
        if self.thinking or self.game_over:
            return
        if self.engine.turn == self.human and self.engine.stack:
            self.engine.unmake()
        if self.engine.turn != self.human and self.engine.stack:
            self.engine.unmake()
        self.selected = None
        self.legal_moves = []
        self._draw()
        self._update_status()


# ---------------- Tic-Tac-Toe ----------------

class TicTacToeWindow(tk.Toplevel):
    SIZE = 140

    def __init__(self, app=None):
        super().__init__(app)
        self.title("Tic-Tac-Toe")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.board = [""] * 9
        self.turn = "X"
        self.game_over = False
        self.scores = {"X": 0, "O": 0, "T": 0}

        _header(self, self, "Tic-Tac-Toe", "you are X")
        self.lbl = tk.Label(self, text="Your turn", font=("Segoe UI", 11, "bold"), bg=BG, fg=TEXT)
        self.lbl.pack()
        self.cv = tk.Canvas(self, width=3 * self.SIZE, height=3 * self.SIZE, bg=BG, highlightthickness=0)
        self.cv.pack(padx=16, pady=8)
        self.cv.bind("<Button-1>", self._click)
        row = tk.Frame(self, bg=BG)
        row.pack(pady=(0, 12))
        _btn2(row, "New game", self._reset).pack(side="left", padx=4)
        self.score_lbl = tk.Label(row, text="X 0 - 0 O  |  0 draws", font=("Segoe UI", 9),
                                  bg=BG, fg=MUTED)
        self.score_lbl.pack(side="left", padx=12)
        self._draw()
        self._update_lbl()

    def _draw(self):
        c = self.cv
        c.delete("all")
        for i in range(4):
            if i % 2 == 1:
                continue
        for i in range(1, 3):
            c.create_line(i * self.SIZE, 8, i * self.SIZE, 3 * self.SIZE - 8, fill=CARD2, width=4)
            c.create_line(8, i * self.SIZE, 3 * self.SIZE - 8, i * self.SIZE, fill=CARD2, width=4)
        font = tkfont.Font(family="Segoe UI", size=64, weight="bold")
        for i in range(9):
            r, col = divmod(i, 3)
            x = col * self.SIZE + self.SIZE // 2
            y = r * self.SIZE + self.SIZE // 2
            if self.board[i] == "X":
                c.create_text(x, y, text="X", font=font, fill=ACC)
            elif self.board[i] == "O":
                c.create_text(x, y, text="O", font=font, fill=RED)

    def _click(self, event):
        if self.game_over:
            return
        col = event.x // self.SIZE
        r = event.y // self.SIZE
        i = r * 3 + col
        if self.board[i] != "":
            return
        self.board[i] = "X"
        self._draw()
        if self._check_win("X"):
            self._end("You win!", "X")
            return
        if "" not in self.board:
            self._end("Draw!", "T")
            return
        self.turn = "O"
        self.lbl.config(text="AI thinking\u2026", fg=MUTED)
        self._draw()
        self.after(10, self._ai_move)

    def _ai_move(self):
        i = self._best()
        if i is None:
            return
        self.board[i] = "O"
        self._draw()
        if self._check_win("O"):
            self._end("AI wins!", "O")
            return
        if "" not in self.board:
            self._end("Draw!", "T")
            return
        self.turn = "X"
        self.lbl.config(text="Your turn", fg=TEXT)

    def _best(self):
        def mm(me, scores):
            w = self._winner()
            if w == me:
                return 10
            if w == ("O" if me == "X" else "X"):
                return -10
            if "" not in self.board:
                return 0
            best = -11
            for i in range(9):
                if self.board[i] == "":
                    self.board[i] = me
                    v = -mm("O" if me == "X" else "X", scores)
                    self.board[i] = ""
                    best = max(best, v)
            return best
        best = -11
        choice = None
        for i in range(9):
            if self.board[i] == "":
                self.board[i] = "O"
                v = -mm("X", None)
                self.board[i] = ""
                if v > best:
                    best = v
                    choice = i
        return choice

    def _winner(self):
        for a, b, c in ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)):
            if self.board[a] and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]
        return None

    def _check_win(self, who):
        return self._winner() == who

    def _end(self, msg, score_key):
        self.game_over = True
        self.scores[score_key] += 1
        self.lbl.config(text=msg, fg=GREEN if score_key == "X" else (RED if score_key == "O" else MUTED))
        self._update_lbl()

    def _reset(self):
        self.board = [""] * 9
        self.turn = "X"
        self.game_over = False
        self._draw()
        self.lbl.config(text="Your turn", fg=TEXT)

    def _update_lbl(self):
        self.score_lbl.config(text=f"X {self.scores['X']} - {self.scores['O']} O  |  {self.scores['T']} draws")


# ---------------- Connect 4 ----------------

class Connect4Window(tk.Toplevel):
    COLS, ROWS = 7, 6
    CELL = 66

    def __init__(self, app=None):
        super().__init__(app)
        self.title("Connect 4")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.board = [[None] * self.COLS for _ in range(self.ROWS)]
        self.player = "r"
        self.ai = "y"
        self.game_over = False
        self.thinking = False

        _header(self, self, "Connect 4", "click a column to drop - you are red")
        self.lbl = tk.Label(self, text="Your move", font=("Segoe UI", 11, "bold"), bg=BG, fg=TEXT)
        self.lbl.pack()
        self.cv = tk.Canvas(self, width=self.COLS * self.CELL, height=self.ROWS * self.CELL,
                            bg=BG, highlightthickness=0)
        self.cv.pack(padx=16, pady=8)
        self.cv.bind("<Button-1>", self._click)
        row = tk.Frame(self, bg=BG)
        row.pack(pady=(0, 12))
        _btn2(row, "New game", self._reset).pack(side="left", padx=4)
        self._draw()

    def _draw(self):
        c = self.cv
        c.delete("all")
        for r in range(self.ROWS):
            for col in range(self.COLS):
                x, y = col * self.CELL, r * self.CELL
                c.create_oval(x + 4, y + 4, x + self.CELL - 4, y + self.CELL - 4,
                              fill="#1b2030", outline=CARD2)
                p = self.board[r][col]
                if p:
                    color = "#ff5252" if p == "r" else "#ffd166"
                    c.create_oval(x + 4, y + 4, x + self.CELL - 4, y + self.CELL - 4,
                                  fill=color, outline="")

    def _click(self, event):
        if self.game_over or self.thinking:
            return
        col = event.x // self.CELL
        if col >= self.COLS:
            return
        self._drop(col, self.player)
        if self._winner() == self.player:
            self._end("You win!", GREEN)
            return
        if self._full():
            self._end("Draw!", MUTED)
            return
        self.thinking = True
        self.lbl.config(text="AI thinking\u2026", fg=MUTED)
        threading.Thread(target=self._ai_worker, daemon=True).start()

    def _drop(self, col, who):
        for r in range(self.ROWS - 1, -1, -1):
            if self.board[r][col] is None:
                self.board[r][col] = who
                self._draw()
                return r
        return None

    def _winner(self):
        b = self.board
        for r in range(self.ROWS):
            for col in range(self.COLS):
                p = b[r][col]
                if not p:
                    continue
                if col + 3 < self.COLS and p == b[r][col + 1] == b[r][col + 2] == b[r][col + 3]:
                    return p
                if r + 3 < self.ROWS and p == b[r + 1][col] == b[r + 2][col] == b[r + 3][col]:
                    return p
                if r + 3 < self.ROWS and col + 3 < self.COLS and p == b[r + 1][col + 1] == b[r + 2][col + 2] == b[r + 3][col + 3]:
                    return p
                if r + 3 < self.ROWS and col - 3 >= 0 and p == b[r + 1][col - 1] == b[r + 2][col - 2] == b[r + 3][col - 3]:
                    return p
        return None

    def _full(self):
        return all(all(cell for cell in row) for row in self.board)

    def _ai_worker(self):
        col = self._best_col()
        try:
            if self.winfo_exists():
                self.after(0, lambda: self._apply_ai(col))
        except Exception:
            pass

    def _apply_ai(self, col):
        self.thinking = False
        if col is None:
            return
        self._drop(col, self.ai)
        if self._winner() == self.ai:
            self._end("AI wins!", RED)
            return
        if self._full():
            self._end("Draw!", MUTED)
            return
        self.lbl.config(text="Your move", fg=TEXT)

    def _best_col(self):
        def eval_board(b):
            score = 0
            for r in range(self.ROWS):
                for col in range(self.COLS - 3):
                    score += _seg(b[r][col:col + 4])
            for col in range(self.COLS):
                for r in range(self.ROWS - 3):
                    score += _seg([b[r + k][col] for k in range(4)])
            for r in range(self.ROWS - 3):
                for col in range(self.COLS - 3):
                    score += _seg([b[r + k][col + k] for k in range(4)])
                    score += _seg([b[r + 3 - k][col + k] for k in range(4)])
            return score

        def _seg(seg):
            p = sum(1 for x in seg if x == self.ai)
            o = sum(1 for x in seg if x == self.player)
            if p and o:
                return 0
            if p == 4:
                return 10000
            if o == 4:
                return -10000
            if p == 3 and o == 0:
                return 60
            if p == 2 and o == 0:
                return 12
            if o == 3 and p == 0:
                return -70
            if o == 2 and p == 0:
                return -14
            return 0

        def drop_at(b, col, who):
            for r in range(self.ROWS - 1, -1, -1):
                if b[r][col] is None:
                    b[r][col] = who
                    return r
            return None

        def negamax(b, depth, who, alpha, beta):
            w = self._winner()
            if w == who:
                return 100000 + depth
            if w is not None and w != who:
                return -(100000 + depth)
            if self._full() or depth == 0:
                return eval_board(b)
            other = self.player if who == self.ai else self.ai
            order = sorted(range(self.COLS), key=lambda c: abs(c - self.COLS // 2))
            best = -10 ** 9
            for col in order:
                if b[0][col] is not None:
                    continue
                r = drop_at(b, col, who)
                v = -negamax(b, depth - 1, other, -beta, -alpha)
                b[r][col] = None
                if v > best:
                    best = v
                if v > alpha:
                    alpha = v
                if alpha >= beta:
                    break
            return best

        order = sorted(range(self.COLS), key=lambda c: abs(c - self.COLS // 2))
        best = -10 ** 9
        choice = None
        for col in order:
            if self.board[0][col] is not None:
                continue
            r = drop_at(self.board, col, self.ai)
            v = -negamax(self.board, 5, self.player, -10 ** 9, 10 ** 9)
            self.board[r][col] = None
            if v > best:
                best = v
                choice = col
        return choice

    def _end(self, msg, color):
        self.game_over = True
        self.lbl.config(text=msg, fg=color)

    def _reset(self):
        self.board = [[None] * self.COLS for _ in range(self.ROWS)]
        self.game_over = False
        self.thinking = False
        self.lbl.config(text="Your move", fg=TEXT)
        self._draw()


# ---------------- Snake ----------------

class SnakeWindow(tk.Toplevel):
    COLS, ROWS = 24, 16
    CELL = 26

    def __init__(self, app=None):
        super().__init__(app)
        self.title("Snake")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.high = _load_scores().get("snake", 0)
        self._reset_state()

        _header(self, self, "Snake", "use arrow keys")
        self.score_lbl = tk.Label(self, text="Score 0   High 0", font=("Segoe UI", 10, "bold"),
                                  bg=BG, fg=TEXT)
        self.score_lbl.pack()
        self.cv = tk.Canvas(self, width=self.COLS * self.CELL, height=self.ROWS * self.CELL,
                            bg="#0a0714", highlightthickness=0)
        self.cv.pack(padx=16, pady=8)
        self.bind("<KeyPress>", self._key)
        self.focus_set()
        self._step()

    def _reset_state(self):
        cx, cy = self.COLS // 2, self.ROWS // 2
        self.snake = [(cx - 2, cy), (cx - 1, cy), (cx, cy)]
        self.dir = (1, 0)
        self.next_dir = (1, 0)
        self.dead = False
        self.score = 0
        self._spawn_food()

    def _spawn_food(self):
        free = [(x, y) for x in range(self.COLS) for y in range(self.ROWS)
                if (x, y) not in self.snake]
        if free:
            self.food = random.choice(free)

    def _key(self, e):
        if self.dead:
            if e.keysym in ("r", "R"):
                self._reset_state()
                self._draw()
            return
        d = {"Left": (-1, 0), "Right": (1, 0), "Up": (0, -1), "Down": (0, 1)}.get(e.keysym)
        if d and not (d[0] == -self.dir[0] and d[1] == -self.dir[1]):
            self.next_dir = d

    def _step(self):
        if not self.dead:
            self.dir = self.next_dir
            head = (self.snake[-1][0] + self.dir[0], self.snake[-1][1] + self.dir[1])
            if (head[0] < 0 or head[0] >= self.COLS or head[1] < 0 or head[1] >= self.ROWS
                    or head in self.snake):
                self.dead = True
            else:
                self.snake.append(head)
                if head == self.food:
                    self.score += 1
                    self._spawn_food()
                else:
                    self.snake.pop(0)
        self._draw()
        self.after(max(70, 120 - 2 * len(self.snake)), self._step)

    def _draw(self):
        c = self.cv
        c.delete("all")
        for x, y in self.snake[:-1]:
            c.create_rectangle(x * self.CELL + 1, y * self.CELL + 1,
                               (x + 1) * self.CELL - 1, (y + 1) * self.CELL - 1,
                               fill="#39ff8c", outline="#1f8f56")
        hx, hy = self.snake[-1]
        c.create_rectangle(hx * self.CELL + 1, hy * self.CELL + 1,
                           (hx + 1) * self.CELL - 1, (hy + 1) * self.CELL - 1,
                           fill="#9dffc4", outline="#1f8f56")
        fx, fy = self.food
        c.create_oval(fx * self.CELL + 4, fy * self.CELL + 4,
                      (fx + 1) * self.CELL - 4, (fy + 1) * self.CELL - 4, fill="#ff2255", outline="")
        self.score_lbl.config(text=f"Score {self.score}   High {max(self.high, self.score)}")
        if self.dead:
            if self.score > self.high:
                self.high = self.score
                data = _load_scores()
                data["snake"] = self.high
                _save_scores(data)
            c.create_text(self.cv.winfo_width() // 2, self.cv.winfo_height() // 2 - 20,
                          text="GAME OVER", fill=RED, font=tkfont.Font(family="Segoe UI", size=30, weight="bold"))
            c.create_text(self.cv.winfo_width() // 2, self.cv.winfo_height() // 2 + 24,
                          text=f"Score {self.score}   High {self.high}   \u2014  press R to restart",
                          fill=TEXT, font=("Segoe UI", 12))


# ---------------- 2048 ----------------

class Tile2048Window(tk.Toplevel):
    SIZE = 4
    CELL = 120
    COLORS = {2: "#eee4da", 4: "#ede0c8", 8: "#f2b179", 16: "#f59563", 32: "#f67c5f",
              64: "#f65e3b", 128: "#edcf72", 256: "#edcc61", 512: "#edc850",
              1024: "#edc53f", 2048: "#edc22e"}

    def __init__(self, app=None):
        super().__init__(app)
        self.title("2048")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.high = _load_scores().get("2048", 0)
        self._reset_state()

        _header(self, self, "2048", "arrow keys to slide and merge")
        self.lbl = tk.Label(self, text="Score 0   High 0", font=("Segoe UI", 11, "bold"), bg=BG, fg=TEXT)
        self.lbl.pack()
        self.cv = tk.Canvas(self, width=self.SIZE * self.CELL + 12, height=self.SIZE * self.CELL + 12,
                            bg=CARD, highlightthickness=0)
        self.cv.pack(padx=16, pady=8)
        self.bind("<KeyPress>", self._key)
        self.focus_set()
        self._draw()

    def _reset_state(self):
        self.grid = [[0] * self.SIZE for _ in range(self.SIZE)]
        self.score = 0
        self.over = False
        self._spawn()
        self._spawn()

    def _spawn(self):
        empty = [(r, c) for r in range(self.SIZE) for c in range(self.SIZE) if self.grid[r][c] == 0]
        if not empty:
            return
        r, c = random.choice(empty)
        self.grid[r][c] = 2 if random.random() < 0.9 else 4

    def _key(self, e):
        if self.over:
            if e.keysym in ("r", "R"):
                self._reset_state()
                self._draw()
            return
        m = {"Left": (0, -1), "Right": (0, 1), "Up": (-1, 0), "Down": (1, 0)}.get(e.keysym)
        if m:
            self._move(m)

    def _move(self, d):
        dr, dc = d
        moved = False
        merged = [[False] * self.SIZE for _ in range(self.SIZE)]
        rrange = range(self.SIZE - 1, -1, -1) if dr == 1 else range(self.SIZE)
        crange = range(self.SIZE - 1, -1, -1) if dc == 1 else range(self.SIZE)
        for r in rrange:
            for c in crange:
                if self.grid[r][c] == 0:
                    continue
                rr, cc = r, c
                while True:
                    nr, nc = rr + dr, cc + dc
                    if not (0 <= nr < self.SIZE and 0 <= nc < self.SIZE):
                        break
                    if self.grid[nr][nc] == 0:
                        rr, cc = nr, nc
                    else:
                        break
                if (0 <= rr + dr < self.SIZE and 0 <= cc + dc < self.SIZE
                        and self.grid[rr + dr][cc + dc] == self.grid[r][c]
                        and not merged[rr + dr][cc + dc]):
                    self.grid[rr + dr][cc + dc] *= 2
                    self.grid[r][c] = 0
                    self.score += self.grid[rr + dr][cc + dc]
                    merged[rr + dr][cc + dc] = True
                    moved = True
                elif (rr, cc) != (r, c):
                    self.grid[rr][cc] = self.grid[r][c]
                    self.grid[r][c] = 0
                    moved = True
        if moved:
            self._spawn()
            self._draw()
            if self._no_moves():
                self.over = True
                self._draw()
        self.lbl.config(text=f"Score {self.score}   High {max(self.high, self.score)}")
        if self.score > self.high:
            self.high = self.score
            data = _load_scores()
            data["2048"] = self.high
            _save_scores(data)

    def _no_moves(self):
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                if self.grid[r][c] == 0:
                    return False
                for dr, dc in ((1, 0), (0, 1)):
                    nr, nc = r + dr, c + dc
                    if nr < self.SIZE and nc < self.SIZE and self.grid[nr][nc] == self.grid[r][c]:
                        return False
        return True

    def _draw(self):
        c = self.cv
        c.delete("all")
        pad = 6
        for r in range(self.SIZE):
            for col in range(self.SIZE):
                x = col * self.CELL + pad
                y = r * self.CELL + pad
                v = self.grid[r][col]
                c.create_rectangle(x, y, x + self.CELL - 2 * pad, y + self.CELL - 2 * pad,
                                   fill="#221a3d", outline="")
                if v:
                    c.create_rectangle(x, y, x + self.CELL - 2 * pad, y + self.CELL - 2 * pad,
                                       fill=self.COLORS.get(v, "#3c3c3c"), outline="")
                    fg = "#776e65" if v < 8 else "#f9f6f2"
                    c.create_text(x + (self.CELL - 2 * pad) // 2, y + (self.CELL - 2 * pad) // 2,
                                  text=str(v), fill=fg,
                                  font=tkfont.Font(family="Segoe UI", size=30 if v < 100 else 22, weight="bold"))
        if self.over:
            c.create_rectangle(0, 0, 999, 999, fill="#000000", stipple="gray50")
            c.create_text(self.cv.winfo_width() // 2, self.cv.winfo_height() // 2 - 12,
                          text="GAME OVER", fill=RED,
                          font=tkfont.Font(family="Segoe UI", size=30, weight="bold"))
            c.create_text(self.cv.winfo_width() // 2, self.cv.winfo_height() // 2 + 24,
                          text=f"Score {self.score} \u2014 press R to restart", fill=TEXT, font=("Segoe UI", 12))


# ---------------- Wordle ----------------

WORDS = ("about above abuse actor acute admit adopt adult after again agent agree ahead alarm album alert "
         "alien align alive allow alone along alter angel anger angle angry apart apple apply arena argue arise "
         "armor array arrow aside asset audio audit avoid award aware awful badge basic battle beach beard beast "
         "begin being below bench berry birth black blade blame blank blast blaze bleed blend bless blind block "
         "blood bloom board boost booth bound brain brand brave bread break breed brick bride brief bring broad "
         "broke brown brush build built bunch burst buyer cabin cable candy carry catch cause chain chair chaos "
         "charm chart chase cheap check chess chest chief child chill chord chunk civic civil claim class clean "
         "clear clerk click cliff climb clock close cloth cloud coach coast could count court cover crack craft "
         "crash crazy cream crime cross crowd crown crush cycle daily dance dirty doubt dough dozen draft drain "
         "drama dream dress drift drill drink drive drone eager eagle early earth eight elect elite empty enemy "
         "enjoy enter entry equal error event every exact exist extra fairy faith false fancy fatal fault favor "
         "feast fence ferry fetch fever fifth fifty fight final first flame flash fleet flesh fling float flood "
         "floor flour fluid flush focus force forge forty forum found frame fraud fresh front frost fruit fully "
         "funny genre ghost giant given glass globe glory glove going grace grade grain grand grant grape graph "
         "grasp grass grave great green greet grief grill grind gross group grove grown guard guess guest guide "
         "guilt habit happy harsh haste haunt heart heavy hello honey honor horse hotel house human humid humor "
         "ideal image imply index inner input irony issue ivory joint judge juice jumbo kayak knife knock known "
         "label labor large laser later laugh layer learn lease leave legal lemon level light limit linen liver "
         "local lodge logic loose lover lower lucky lunch lyric magic major maker march match maybe mayor medal "
         "media melon mercy merge merit merry metal meter micro might minor minus mixed model money month moral "
         "motor mount mouse mouth movie music nerve never night noble noise north noted novel nurse occur ocean "
         "offer often olive onion onset opera orbit order organ other ought outer owner oxide ozone paint panel "
         "panic paper party pasta patch pause peace pearl penny perch phone photo piano piece pilot pitch pixel "
         "pizza place plain plane plant plate plaza point polar porch power press price pride prime print prior "
         "prize probe proof proud prove proxy pulse punch pupil purse quilt quote racer radar radio raise rally "
         "ranch range rapid ratio reach react ready realm rebel refer reign relax relay relic remix renew reply "
         "rider ridge rifle right rigid rinse ripen risky rival river roast robot rocky roman rough round route "
         "royal rugby ruins rural saint salad salsa sandy sauce scale scarf scene scent scope score scout scrap "
         "screw scrub seize sense serve setup seven shade shaft shake shall shame shape share shark sharp sheep "
         "sheet shelf shell shift shine shirt shock shoot shore short shout shove shown shrub sight since siren "
         "sixth sixty skate skill skirt skull slate slave sleep slice slide slope small smart smash smell smile "
         "smoke smooth snack snake solar solid solve sorry sound south space spare spark speak spear speed spend "
         "spent spice spike spine spite split spoke spoon sport spray squad stack staff stage stain stake stale "
         "stamp stand stare stark start state steam steel steep steer stern stick stiff still sting stock stone "
         "stood stool store storm story stove strap straw strip stuck study stuff style sugar suite sunny super "
         "sure surge swear sweat sweep sweet swell swift swing sword syrup table taken taste teach teeth tempt "
         "tense tenth thank theft their theme there these thick thief thing think third thorn those three throw "
         "thumb tiger tight timer tired title toast today token topic total touch tough towel tower toxic trace "
         "track trade trail train trait trash treat trend trial tribe trick troop truck truly trunk trust truth "
         "tutor twice twist ultra uncle under undue unfit union unite unity until upper upset urban usage usual "
         "utter vague valid value valve vapor vault venue verse video vigor viral virus visit vital vivid vocal "
         "voice voter vowel wagon waist waste watch water weary weave wedge weigh weird wheel where which while "
         "whine whirl white whole whose widen width witch woman world worry worse worst worth would wound wrist "
         "write wrong wrote young youth zebra").split()

WORD_COLORS = {"green": "#538d4e", "yellow": "#b59f3b", "gray": "#3a3a3c", "key": "#565758"}


class WordleWindow(tk.Toplevel):
    ROWS, COLS = 6, 5
    CELL = 54

    def __init__(self, app=None):
        super().__init__(app)
        self.title("Wordle")
        self.configure(bg=BG)
        self.resizable(False, False)
        self._new_word()

        _header(self, self, "Wordle", "guess the 5-letter word in 6 tries")
        self.cv = tk.Canvas(self, width=self.COLS * self.CELL + 20, height=self.ROWS * self.CELL + 20,
                            bg=BG, highlightthickness=0)
        self.cv.pack(padx=12, pady=(6, 2))
        self._build_keys()
        self.bind("<KeyPress>", self._key)
        self.focus_set()
        self._draw()

    def _new_word(self):
        self.word = random.choice(WORDS)
        self.guesses = []
        self.current = ""
        self.done = False
        self.hint = ""

    def _build_keys(self):
        rows = ("QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM")
        kf = tk.Frame(self, bg=BG)
        kf.pack(pady=(0, 12))
        for ri, row in enumerate(rows):
            rf = tk.Frame(kf, bg=BG)
            rf.pack()
            if ri == 2:
                tk.Button(rf, text="\u232B", command=self._back, bg=WORD_COLORS["key"], fg=TEXT,
                          activebackground="#6a6a6c", activeforeground=TEXT, relief="flat", bd=0,
                          width=3, font=("Segoe UI", 10), cursor="hand2").pack(side="left", padx=2, pady=2)
            for ch in row:
                b = tk.Button(rf, text=ch, command=lambda c=ch: self._type(c),
                              bg=WORD_COLORS["key"], fg=TEXT, activebackground="#6a6a6c",
                              activeforeground=TEXT, relief="flat", bd=0, width=3,
                              font=("Segoe UI", 10, "bold"), cursor="hand2")
                b.pack(side="left", padx=2, pady=2)
            if ri == 2:
                tk.Button(rf, text="ENTER", command=self._submit, bg=WORD_COLORS["key"], fg=TEXT,
                          activebackground="#6a6a6c", activeforeground=TEXT, relief="flat", bd=0,
                          width=5, font=("Segoe UI", 10, "bold"), cursor="hand2").pack(side="left", padx=2, pady=2)

    def _key(self, e):
        if e.keysym == "Return":
            self._submit()
        elif e.keysym == "BackSpace":
            self._back()
        elif e.char and e.char.isalpha():
            self._type(e.char.upper())

    def _type(self, ch):
        if self.done or len(self.current) < self.COLS:
            if len(self.current) < self.COLS:
                self.current += ch.upper()
                self._draw()

    def _back(self):
        if not self.done and self.current:
            self.current = self.current[:-1]
            self._draw()

    def _submit(self):
        if self.done or len(self.current) != self.COLS:
            return
        self.guesses.append(self.current.upper())
        if self.current.upper() == self.word.upper():
            self.done = True
            self._draw()
            self._win()
            return
        if len(self.guesses) == self.ROWS:
            self.done = True
            self._draw()
            self._lose()
        self.current = ""
        self._draw()

    def _feedback(self, guess):
        word = self.word.upper()
        guess = guess.upper()
        res = [None] * self.COLS
        counts = {}
        for ch in word:
            counts[ch] = counts.get(ch, 0) + 1
        for i, (g, w) in enumerate(zip(guess, word)):
            if g == w:
                res[i] = "green"
                counts[g] -= 1
        for i, (g, w) in enumerate(zip(guess, word)):
            if res[i] is None:
                if counts.get(g, 0) > 0:
                    res[i] = "yellow"
                    counts[g] -= 1
                else:
                    res[i] = "gray"
        return res

    def _draw(self):
        c = self.cv
        c.delete("all")
        for i in range(self.ROWS):
            guess = self.guesses[i] if i < len(self.guesses) else ""
            fb = self._feedback(guess) if guess else None
            for j in range(self.COLS):
                x = j * self.CELL + 10
                y = i * self.CELL + 10
                ch = guess[j] if j < len(guess) else (self.current[j] if i == len(self.guesses) and j < len(self.current) else "")
                fill = "#1b2030"
                if fb:
                    fill = WORD_COLORS[fb[j]]
                c.create_rectangle(x, y, x + self.CELL - 8, y + self.CELL - 8,
                                   fill=fill, outline="#3a3a3c" if not fb else fill, width=2)
                if ch:
                    c.create_text(x + (self.CELL - 8) // 2, y + (self.CELL - 8) // 2, text=ch,
                                  fill="#ffffff", font=tkfont.Font(family="Segoe UI", size=22, weight="bold"))
        if self.done:
            c.create_text(self.cv.winfo_width() // 2, self.cv.winfo_height() // 2,
                          text="New game?  press R", fill=TEXT, font=("Segoe UI", 12, "bold"))

    def _win(self):
        tries = len(self.guesses)
        msg = f"Got it in {tries} {'try' if tries == 1 else 'tries'}! Word was {self.word.upper()}"
        messagebox.showinfo("Wordle", msg, parent=self)

    def _lose(self):
        messagebox.showinfo("Wordle", f"The word was {self.word.upper()}. Press R for a new word.", parent=self)


# ---------------- Memory ----------------

MEMO_ICONS = ["\u2660", "\u2665", "\u2666", "\u2663", "\u2605", "\u263E", "\u2600", "\u266A"]


class MemoryWindow(tk.Toplevel):
    N = 4
    CELL = 88

    def __init__(self, app=None):
        super().__init__(app)
        self.title("Memory")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.high = _load_scores().get("memory", 0)
        self._reset()

        _header(self, self, "Memory", "flip two cards to find pairs")
        self.lbl = tk.Label(self, text="Moves 0   High 0", font=("Segoe UI", 10, "bold"), bg=BG, fg=TEXT)
        self.lbl.pack()
        self.cv = tk.Canvas(self, width=self.N * self.CELL + 20, height=self.N * self.CELL + 20,
                            bg=BG, highlightthickness=0)
        self.cv.pack(padx=16, pady=8)
        self.cv.bind("<Button-1>", self._click)
        row = tk.Frame(self, bg=BG)
        row.pack(pady=(0, 12))
        _btn2(row, "New game", self._reset).pack()
        self._draw()

    def _reset(self):
        deck = MEMO_ICONS * 2
        random.shuffle(deck)
        self.cards = deck
        self.revealed = [False] * (self.N * self.N)
        self.locked = [False] * (self.N * self.N)
        self.open = []
        self.moves = 0
        self.start = None
        self.finished = False

    def _click(self, event):
        if self.finished:
            return
        col = event.x // self.CELL
        r = event.y // self.CELL
        if col >= self.N or r >= self.N:
            return
        i = r * self.N + col
        if self.locked[i] or self.revealed[i]:
            return
        self.revealed[i] = True
        self.open.append(i)
        self._draw()
        if len(self.open) == 2:
            self.moves += 1
            a, b = self.open
            if self.cards[a] == self.cards[b]:
                self.locked[a] = self.locked[b] = True
                self.open = []
                if all(self.locked):
                    self._win()
            else:
                self.after(600, self._flip_back)
        self.lbl.config(text=f"Moves {self.moves}   High {self.high or '-'}")

    def _flip_back(self):
        for i in self.open:
            self.revealed[i] = False
        self.open = []
        self._draw()

    def _win(self):
        self.finished = True
        self._draw()
        if self.high == 0 or self.moves < self.high:
            self.high = self.moves
            data = _load_scores()
            data["memory"] = self.high
            _save_scores(data)
        self.lbl.config(text=f"You finished in {self.moves} moves!  High {self.high}", fg=GREEN)

    def _draw(self):
        c = self.cv
        c.delete("all")
        for i in range(self.N * self.N):
            r, col = divmod(i, self.N)
            x = col * self.CELL + 10
            y = r * self.CELL + 10
            show = self.revealed[i]
            fill = CARD2 if show else ACC
            c.create_rectangle(x, y, x + self.CELL - 8, y + self.CELL - 8, fill=fill, outline="")
            if show:
                c.create_text(x + (self.CELL - 8) // 2, y + (self.CELL - 8) // 2,
                              text=self.cards[i], fill=TEXT,
                              font=tkfont.Font(family="Segoe UI Symbol", size=34))
            elif not self.finished:
                c.create_text(x + (self.CELL - 8) // 2, y + (self.CELL - 8) // 2,
                              text="\u2753", fill="#0d1220",
                              font=tkfont.Font(family="Segoe UI", size=26))


# ---------------- Minesweeper ----------------

MINE_NUM_COLORS = {
    1: "#00f0ff", 2: "#39ff8c", 3: "#ff2255", 4: "#9d7bff",
    5: "#ffb86c", 6: "#4fd6d6", 7: "#eaf2ff", 8: "#8f87c2",
}


class MinesweeperWindow(tk.Toplevel):
    N = 9
    MINES = 10
    CELL = 40

    def __init__(self, app=None):
        super().__init__(app)
        self.title("Minesweeper")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.wins = _load_scores().get("minesweeper_wins", 0)
        self._reset()

        _header(self, self, "Minesweeper", "left-click to clear, right-click to flag")
        self.lbl = tk.Label(self, text="", font=("Segoe UI", 10, "bold"), bg=BG, fg=TEXT)
        self.lbl.pack()
        self.cv = tk.Canvas(self, width=self.N * self.CELL, height=self.N * self.CELL,
                            bg="#0a0714", highlightthickness=0)
        self.cv.pack(padx=16, pady=8)
        self.cv.bind("<Button-1>", self._left_click)
        self.cv.bind("<Button-3>", self._right_click)
        row = tk.Frame(self, bg=BG)
        row.pack(pady=(0, 12))
        _btn2(row, "New game", self._new_game).pack()
        self._draw()
        self._update_lbl()

    def _reset(self):
        n2 = self.N * self.N
        self.mine = [False] * n2
        self.adjacent = [0] * n2
        self.revealed = [False] * n2
        self.flagged = [False] * n2
        self.started = False
        self.game_over = False
        self.won = False

    def _new_game(self):
        self._reset()
        self._draw()
        self._update_lbl()

    def _neighbors(self, i):
        r, col = divmod(i, self.N)
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, col + dc
                if 0 <= nr < self.N and 0 <= nc < self.N:
                    yield nr * self.N + nc

    def _place_mines(self, safe_i):
        # Mines are placed on the first click, never on the clicked cell
        # itself, so the player is never blown up before they've done
        # anything - classic Minesweeper behavior.
        pool = [i for i in range(self.N * self.N) if i != safe_i]
        for i in random.sample(pool, self.MINES):
            self.mine[i] = True
        for i in range(self.N * self.N):
            if not self.mine[i]:
                self.adjacent[i] = sum(1 for n in self._neighbors(i) if self.mine[n])
        self.started = True

    def _flood_reveal(self, start):
        stack = [start]
        while stack:
            i = stack.pop()
            if self.revealed[i] or self.flagged[i]:
                continue
            self.revealed[i] = True
            if self.adjacent[i] == 0:
                for n in self._neighbors(i):
                    if not self.revealed[n] and not self.mine[n]:
                        stack.append(n)

    def _cell_at(self, event):
        col = event.x // self.CELL
        r = event.y // self.CELL
        if col >= self.N or r >= self.N:
            return None
        return r * self.N + col

    def _left_click(self, event):
        if self.game_over:
            return
        i = self._cell_at(event)
        if i is None or self.flagged[i] or self.revealed[i]:
            return
        if not self.started:
            self._place_mines(i)
        if self.mine[i]:
            self.revealed[i] = True
            self.game_over = True
            self._draw()
            self.lbl.config(text="Boom! You hit a mine.", fg=RED)
            return
        self._flood_reveal(i)
        if sum(1 for j in range(self.N * self.N) if not self.mine[j] and not self.revealed[j]) == 0:
            self.game_over = True
            self.won = True
            self.wins += 1
            data = _load_scores()
            data["minesweeper_wins"] = self.wins
            _save_scores(data)
            self.lbl.config(text=f"Cleared it! Wins: {self.wins}", fg=GREEN)
            self._draw()
            return
        self._draw()
        self._update_lbl()

    def _right_click(self, event):
        if self.game_over:
            return
        i = self._cell_at(event)
        if i is None or self.revealed[i]:
            return
        self.flagged[i] = not self.flagged[i]
        self._draw()
        self._update_lbl()

    def _update_lbl(self):
        if self.game_over:
            return
        flags = sum(self.flagged)
        self.lbl.config(text=f"Mines {self.MINES}   Flags {flags}   Wins {self.wins}", fg=TEXT)

    def _draw(self):
        c = self.cv
        c.delete("all")
        pad = 2
        for i in range(self.N * self.N):
            r, col = divmod(i, self.N)
            x = col * self.CELL
            y = r * self.CELL
            revealed = self.revealed[i]
            show_mine = self.game_over and self.mine[i]
            if revealed or show_mine:
                fill = "#3a1a1a" if (self.game_over and self.mine[i] and revealed) else CARD2
                c.create_rectangle(x + pad, y + pad, x + self.CELL - pad, y + self.CELL - pad,
                                   fill=fill, outline="")
                if self.mine[i]:
                    c.create_text(x + self.CELL / 2, y + self.CELL / 2, text="\U0001f4a3",
                                  font=tkfont.Font(family="Segoe UI Emoji", size=16))
                elif self.adjacent[i] > 0:
                    n = self.adjacent[i]
                    c.create_text(x + self.CELL / 2, y + self.CELL / 2, text=str(n),
                                  fill=MINE_NUM_COLORS.get(n, TEXT),
                                  font=tkfont.Font(family="Segoe UI", size=14, weight="bold"))
            else:
                c.create_rectangle(x + pad, y + pad, x + self.CELL - pad, y + self.CELL - pad,
                                   fill=ACC, outline="")
                if self.flagged[i]:
                    c.create_text(x + self.CELL / 2, y + self.CELL / 2, text="\U0001f6a9",
                                  font=tkfont.Font(family="Segoe UI Emoji", size=14))

