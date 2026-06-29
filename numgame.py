import pygame
import math
import random
import csv
import os


# ИНИЦИАЛИЗАЦИЯ PYGAME
# Создаём окно игры и часы для контроля FPS

pygame.init()
screen = pygame.display.set_mode((600, 600))
clock = pygame.time.Clock()
pygame.display.set_caption("Lottery")


# ЗВУК СПИНА
# Загружаем music.mp3 (должен лежать в той же папке, что и скрипт)
# и проигрываем его каждый раз, когда колесо начинает крутиться.

spin_sound = pygame.mixer.Sound(os.path.join(os.path.dirname(__file__), "music.mp3"))



# ЗАГРУЗКА ТЕМ ИЗ CSV
# Читает themes.csv (лежит в той же папке, что и этот скрипт)
# и возвращает список строк-тем для ящиков

def load_themes(path="themes.csv"):
    full_path = os.path.join(os.path.dirname(__file__), path)
    with open(full_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        return [row[0] for row in reader if row]

THEMES = load_themes()



# НАСТРОЙКИ КОЛЕСА (визуал для спина в самом начале игры)
# sectors      — подписи секторов (числа 1–10)
# colors       — цвета секторов по кругу
# sector_angle — угол одного сектора в градусах

sectors = [str(i) for i in range(1, 11)]
colors = [(231,76,60),(241,196,15)] * 5
sector_angle = 360 / len(sectors)

font = pygame.font.SysFont("Arial", 16)            # мелкий шрифт — подписи секторов
big_font = pygame.font.SysFont("Arial", 72, bold=True)  # крупный шрифт — итоговое число
big_font_small = pygame.font.SysFont("Arial", 28, bold=True)  # средний шрифт — подпись "чья очередь"
box_font = pygame.font.SysFont("Arial", 18)        # шрифт для текста темы внутри ящика

# Переменные анимации вращения
angle = 0                  # текущий угол поворота колеса (для отрисовки)
spin_start_angle = 0       # угол, с которого начался текущий спин
target_angle = 0           # угол, к которому должно прийти колесо в конце спина
spin_start_time = 0        # момент запуска спина (мс, pygame.time.get_ticks())
SPIN_DURATION_MS = 3000    # сколько миллисекунд длится анимация одного спина
result_number = 1          # число, которое выпало в результате спина



# ОТРИСОВКА КОЛЕСА
# Рисует сектора с числами + стрелку-указатель сверху.
# Вызывается каждый кадр, пока идёт анимация спина.

def draw_wheel(angle):
    center = (300, 250)
    radius = 200
    for i, sector in enumerate(sectors):
        # считаем границы сектора в радианах для текущего угла поворота
        start = math.radians(angle + i * sector_angle)
        end = math.radians(angle + (i+1) * sector_angle)

        # строим многоугольник (веер точек), который образует сектор
        points = [center]
        for j in range(21):
            a = start + j*(end-start)/20
            points.append((center[0] + radius*math.cos(a), center[1] + radius*math.sin(a)))
        pygame.draw.polygon(screen, colors[i % len(colors)], points)

        # подпись числа в середине сектора
        mid_angle = start + (end - start) / 2
        text_x = center[0] + (radius * 0.65) * math.cos(mid_angle)
        text_y = center[1] + (radius * 0.65) * math.sin(mid_angle)
        text_surf = font.render(sector, True, (0, 0, 0))
        text_rect = text_surf.get_rect(center=(text_x, text_y))
        screen.blit(text_surf, text_rect)

    # стрелка-указатель (треугольник), показывает на верхний сектор
    pygame.draw.polygon(screen, (0,0,0), [(center[0]-15, 30), (center[0]+15, 30), (center[0], 70)])



# ЗАПУСК СПИНА
# Выбирает случайный итоговый сектор (число 1–10), запоминает его
# в result_number и считает угол, на котором стрелка должна оказаться
# точно по центру этого сектора (target_angle).
# Вращение идёт не через свободное затухание скорости, а через
# интерполяцию по времени от текущего угла к target_angle —
# поэтому колесо ГАРАНТИРОВАННО останавливается на нужном секторе.

def start_spin():
    global spin_start_angle, target_angle, spin_start_time, result_number
    spin_sound.stop()  # на случай, если предыдущий звук ещё не закончился
    spin_sound.play()
    result_number_idx = random.randint(0, len(sectors)-1)
    result_number = sectors[result_number_idx]

    spin_start_angle = angle
    # стрелка стоит сверху (270°/−90° в экранных координатах из-за cos/sin),
    # поэтому считаем угол так, чтобы именно середина нужного сектора
    # оказалась под стрелкой после поворота на 5 полных кругов + остаток
    needed_offset = (270 - (result_number_idx * sector_angle + sector_angle / 2)) % 360
    target_angle = spin_start_angle + 360 * 5 + ((needed_offset - spin_start_angle) % 360)

    # небольшое недокручивание: останавливаемся чуть раньше центра сектора
    # (но всё ещё внутри его границ), чтобы по стрелке нельзя было на глаз
    # угадать число до того, как оно откроется по клику
    target_angle -= random.uniform(4, 10)

    spin_start_time = pygame.time.get_ticks()



# НАСТРОЙКИ ЯЩИКОВ С ТЕМАМИ
# 5 прямоугольников в ряд по центру экрана.
# round_themes   — список из 5 тем, назначенных на текущий раунд
# revealed       — какие ящики уже открыты (True/False на каждый)
# revealed_count — сколько ящиков открыто в текущем раунде

BOX_COUNT = 5


# СЧЁТ КОМАНД И ВВОД ЧИСЛА
# team_scores[0] — очки первой команды, team_scores[1] — второй.
# current_team   — чья сейчас очередь угадывать (0 или 1), чередуется
#                  после каждого раунда.
# guess_text     — то, что игрок успел напечатать с клавиатуры
#                  (строка цифр, отправляется по Enter)

team_scores = [0, 0]
current_team = 0
guess_text = ""

ROUND_COUNT = 6      # сколько раундов длится игра, после — объявляем победителя
round_number = 0     # сколько раундов уже сыграно

# Кнопка "Играть ещё раз" на финальном экране
play_again_rect = pygame.Rect(190, 340, 220, 50)

box_width, box_height = 90, 90
box_gap = 20
total_width = BOX_COUNT * box_width + (BOX_COUNT - 1) * box_gap
start_x = (600 - total_width) // 2
box_y = 250

boxes_rects = [pygame.Rect(start_x + i*(box_width+box_gap), box_y, box_width, box_height) for i in range(BOX_COUNT)]
round_themes = []
revealed = [False] * BOX_COUNT
revealed_count = 0



# НАЧАЛО НОВОГО РАУНДА ЯЩИКОВ
# Выбирает 5 случайных тем из CSV (без повторов внутри раунда,
# если в файле тем хватает) и сбрасывает все ящики в закрытое состояние.
# Вызывается каждый раз, когда число прячется и появляются ящики.

def setup_boxes_round():
    global round_themes, revealed, revealed_count
    if len(THEMES) >= BOX_COUNT:
        round_themes = random.sample(THEMES, BOX_COUNT)   # без повторов
    else:
        round_themes = [random.choice(THEMES) for _ in range(BOX_COUNT)]  # с повторами, если тем мало
    revealed = [False] * BOX_COUNT
    revealed_count = 0



# ОТРИСОВКА ЯЩИКОВ
# Закрытый ящик — серый с "?".
# Открытый ящик — зелёный с текстом темы (с переносом по словам,
# если строка не влезает по ширине ящика).

def draw_boxes():
    for i, rect in enumerate(boxes_rects):
        if revealed[i]:
            pygame.draw.rect(screen, (46, 204, 113), rect, border_radius=8)  # зелёный — открыт
            text = round_themes[i]
        else:
            pygame.draw.rect(screen, (149, 165, 166), rect, border_radius=8)  # серый — закрыт
            text = "?"
        pygame.draw.rect(screen, (0,0,0), rect, 2, border_radius=8)  # чёрная рамка

        # --- разбиваем текст темы на строки, чтобы влезло в ящик ---
        words = text.split(" ")
        lines = []
        cur_line = ""
        for w in words:
            test = (cur_line + " " + w).strip()
            if box_font.size(test)[0] > rect.width - 10:
                lines.append(cur_line)
                cur_line = w
            else:
                cur_line = test
        if cur_line:
            lines.append(cur_line)

        # --- центрируем строки по вертикали внутри ящика ---
        total_h = len(lines) * box_font.get_height()
        start_y = rect.centery - total_h // 2
        for j, line in enumerate(lines):
            surf = box_font.render(line, True, (0,0,0))
            r = surf.get_rect(center=(rect.centerx, start_y + j*box_font.get_height() + box_font.get_height()//2))
            screen.blit(surf, r)



# ОПРЕДЕЛЕНИЕ КЛИКА ПО ЯЩИКУ
# Принимает позицию мыши, возвращает индекс ящика под курсором
# или None, если клик был не по ящику.

def box_index_at(pos):
    for i, rect in enumerate(boxes_rects):
        if rect.collidepoint(pos):
            return i
    return None



# НАЧИСЛЕНИЕ ОЧКОВ ЗА УГАДАННОЕ ЧИСЛО
# Сравнивает введённое число с тем, что выпало на колесе (result_number):
#  - совпало точно        -> 5 очков
#  - отличается на 1 (+-1) -> 3 очка
#  - всё остальное         -> 0 очков
# Очки прибавляются команде current_team, после чего очередь
# переходит к другой команде (чередование команд каждый раунд).

def submit_guess(guess_str):
    global current_team
    if not guess_str:
        return  # пустой ввод -> ничего не засчитываем, ждём цифры

    guess_num = int(guess_str)
    target_num = int(result_number)
    diff = abs(guess_num - target_num)

    if diff == 0:
        points = 5
    elif diff == 1:
        points = 3
    else:
        points = 0

    team_scores[current_team] += points
    current_team = 1 - current_team  # переключаем очередь на другую команду



# СОСТОЯНИЯ ИГРЫ (state machine)
# "start"  — игра ещё не началась, ждём клика для первого спина
# "spin"   — идёт анимация вращения колеса
# "hidden" — колесо остановилось, число скрыто, ждём клика чтобы открыть
# "number" — показано число, ждём клика чтобы скрыть его
# "boxes"  — показаны 5 ящиков, ждём кликов по ним; когда все
#            открыты — клик переводит в "guess"
# "guess"  — команда вводит число с клавиатуры; по Enter число
#            проверяется, очки начисляются, очередь команды
#            меняется; если раунды не закончились — новый спин,
#            иначе игра переходит в "winner"
# "winner" — финальный экран со счётом и победителем, игра окончена

state = "start"
# спин теперь не запускается автоматически — ждём первого клика

running = True
while running:

    
    # ОБРАБОТКА СОБЫТИЙ (закрытие окна + клики мыши)
   
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:

            if state == "start":
                # самый первый клик в игре -> запускаем первый спин
                start_spin()
                state = "spin"

            elif state == "winner":
                # клик по кнопке "Играть ещё раз" -> полный сброс игры
                if play_again_rect.collidepoint(event.pos):
                    team_scores[0] = 0
                    team_scores[1] = 0
                    current_team = 0
                    round_number = 0
                    guess_text = ""
                    start_spin()
                    state = "spin"

            elif state == "hidden":
                # колесо остановилось, число скрыто — клик его открывает
                state = "number"

            elif state == "number":
                # клик по числу -> прячем число, открываем новый раунд ящиков
                setup_boxes_round()
                state = "boxes"

            elif state == "boxes":
                if revealed_count < BOX_COUNT:
                    # не все ящики открыты — проверяем, попал ли клик в закрытый ящик
                    idx = box_index_at(event.pos)
                    if idx is not None and not revealed[idx]:
                        revealed[idx] = True
                        revealed_count += 1
                else:
                    # все 5 тем открыты — клик переводит игру в режим ввода числа
                    guess_text = ""
                    state = "guess"

        if event.type == pygame.KEYDOWN and state == "guess":
            
            # ВВОД ЧИСЛА С КЛАВИАТУРЫ
            # Цифры добавляются в guess_text (максимум 2 символа,
            # т.к. числа от 1 до 10), Backspace стирает последний
            # символ, Enter отправляет ответ на проверку.
            
            if event.unicode.isdigit() and len(guess_text) < 2:
                guess_text += event.unicode
            elif event.key == pygame.K_BACKSPACE:
                guess_text = guess_text[:-1]
            elif event.key == pygame.K_RETURN:
                submit_guess(guess_text)
                guess_text = ""
                round_number += 1

                if round_number >= ROUND_COUNT:
                    state = "winner"     # раунды закончились -> финальный экран
                else:
                    start_spin()         # крутим колесо для следующего раунда
                    state = "spin"

    
    # ОТРИСОВКА КАДРА (зависит от текущего состояния)
    
    screen.fill((255, 255, 255))

    if state == "start":
        # экран ожидания — колесо ещё не крутится, ждём клика
        draw_wheel(0)
        hint = font.render("Клик, чтобы начать игру", True, (120,120,120))
        screen.blit(hint, hint.get_rect(center=(300, 380)))

    elif state == "spin":
        # ease-out интерполяция: быстро в начале, плавно тормозит к концу,
        # и в конце угол ТОЧНО равен target_angle — без рассинхрона с числом
        elapsed = pygame.time.get_ticks() - spin_start_time
        t = min(elapsed / SPIN_DURATION_MS, 1.0)
        eased_t = 1 - (1 - t) ** 3  # кубический ease-out
        angle = spin_start_angle + (target_angle - spin_start_angle) * eased_t
        draw_wheel(angle % 360)
        if t >= 1.0:
            state = "hidden"  # колесо остановилось, но число пока скрыто до клика

    elif state == "hidden":
        # колесо остановилось, но число пока не показано
        hidden_surf = big_font.render("?", True, (150, 150, 150))
        screen.blit(hidden_surf, hidden_surf.get_rect(center=(300, 250)))
        hint = font.render("Клик, чтобы показать число", True, (120,120,120))
        screen.blit(hint, hint.get_rect(center=(300, 350)))

    elif state == "number":
        # крупное число в центре + подсказка под ним
        text_surf = big_font.render(result_number, True, (0, 0, 0))
        text_rect = text_surf.get_rect(center=(300, 250))
        screen.blit(text_surf, text_rect)
        hint = font.render("Клик, чтобы скрыть и открыть ящики", True, (120,120,120))
        screen.blit(hint, hint.get_rect(center=(300, 350)))

    elif state == "boxes":
        # пять ящиков + подсказка, когда все открыты
        draw_boxes()
        if revealed_count == BOX_COUNT:
            hint = font.render("Клик, чтобы ввести число", True, (120,120,120))
            screen.blit(hint, hint.get_rect(center=(300, 380)))

    elif state == "guess":
        # экран ввода числа: чьи очередь, что уже напечатано, подсказка
        turn_label = big_font_small.render(f"Команда {current_team + 1}, вводи число", True, (0, 0, 0))
        screen.blit(turn_label, turn_label.get_rect(center=(300, 180)))

        input_surf = big_font.render(guess_text if guess_text else "_", True, (41, 128, 185))
        screen.blit(input_surf, input_surf.get_rect(center=(300, 260)))

        hint = font.render("Печатай число, Enter — отправить, Backspace — стереть", True, (120,120,120))
        screen.blit(hint, hint.get_rect(center=(300, 340)))

    elif state == "winner":
        # финальный экран: итоговый счёт и победитель (или ничья)
        if team_scores[0] > team_scores[1]:
            winner_text = "Победила Команда 1!"
        elif team_scores[1] > team_scores[0]:
            winner_text = "Победила Команда 2!"
        else:
            winner_text = "Ничья!"

        winner_surf = big_font_small.render(winner_text, True, (0, 0, 0))
        screen.blit(winner_surf, winner_surf.get_rect(center=(300, 220)))

        final_score_surf = big_font_small.render(
            f"{team_scores[0]} : {team_scores[1]}", True, (41, 128, 185)
        )
        screen.blit(final_score_surf, final_score_surf.get_rect(center=(300, 280)))

        # кнопка "Играть ещё раз"
        pygame.draw.rect(screen, (46, 204, 113), play_again_rect, border_radius=10)
        pygame.draw.rect(screen, (0, 0, 0), play_again_rect, 2, border_radius=10)
        btn_text = box_font.render("Играть ещё раз", True, (0, 0, 0))
        screen.blit(btn_text, btn_text.get_rect(center=play_again_rect.center))

   
    # СЧЁТ КОМАНД (виден поверх любого состояния игры)
    
    score1_color = (39, 174, 96) if current_team == 0 and state == "guess" else (0, 0, 0)
    score2_color = (39, 174, 96) if current_team == 1 and state == "guess" else (0, 0, 0)
    score1_surf = font.render(f"Команда 1: {team_scores[0]}", True, score1_color)
    score2_surf = font.render(f"Команда 2: {team_scores[1]}", True, score2_color)
    screen.blit(score1_surf, (15, 15))
    screen.blit(score2_surf, (600 - score2_surf.get_width() - 15, 15))

    if state != "winner":
        round_surf = font.render(f"Раунд {round_number + 1} / {ROUND_COUNT}", True, (100, 100, 100))
        screen.blit(round_surf, round_surf.get_rect(center=(300, 20)))

    
    # ОБНОВЛЕНИЕ ЭКРАНА И ОГРАНИЧЕНИЕ FPS
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()