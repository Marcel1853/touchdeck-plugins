#!/usr/bin/env python3
"""Trägt in plugin.json zu jedem Text { "en", "de" } die weiteren Sprachen ein (fr, es, pl, pt-br, ru, zh-cn).

Aufruf:  python3 tools/i18n_plugin_json.py
Die Übersetzungen sind KI-Übersetzungen (wie bei UTLogistics) – Korrekturen willkommen. Ein englischer
Text ohne Eintrag hier bleibt, wie er ist (TouchDeck fällt dann auf Englisch zurück); das Skript meldet ihn.
"""
import json
import os
import re

LANGS = ["fr", "es", "pl", "pt-br", "ru", "zh-cn"]

# Englisch → (fr, es, pl, pt-br, ru, zh-cn)
TABLE = {
    "Factorio on your buttons: live research, speed, evolution, power and production (with graphs), planet, UTLogistics trains; pause, speed, save, screenshot and research queue. Needs the Factorio mod “TouchDeck Bridge” (mod portal). No launch options, no network: the mod writes JSON files, the plugin watches them.": (
        "Factorio sur vos boutons : recherche, vitesse, évolution, électricité et production en direct (avec graphiques), planète, trains UTLogistics ; pause, vitesse, sauvegarde, capture d'écran et file de recherche. Nécessite le mod Factorio « TouchDeck Bridge » (portail des mods). Sans option de lancement, sans réseau : le mod écrit des fichiers JSON, le plugin les surveille.",
        "Factorio en tus botones: investigación, velocidad, evolución, electricidad y producción en directo (con gráficos), planeta, trenes de UTLogistics; pausa, velocidad, guardar, captura y cola de investigación. Necesita el mod de Factorio «TouchDeck Bridge» (portal de mods). Sin opciones de inicio, sin red: el mod escribe archivos JSON y el plugin los vigila.",
        "Factorio na twoich przyciskach: badania, prędkość, ewolucja, prąd i produkcja na żywo (z wykresami), planeta, pociągi UTLogistics; pauza, prędkość, zapis, zrzut ekranu i kolejka badań. Wymaga moda do Factorio „TouchDeck Bridge” (portal modów). Bez opcji uruchamiania, bez sieci: mod zapisuje pliki JSON, plugin je obserwuje.",
        "Factorio nos seus botões: pesquisa, velocidade, evolução, energia e produção ao vivo (com gráficos), planeta, trens do UTLogistics; pausa, velocidade, salvar, captura de tela e fila de pesquisa. Precisa do mod de Factorio “TouchDeck Bridge” (portal de mods). Sem opções de inicialização, sem rede: o mod grava arquivos JSON e o plugin os observa.",
        "Factorio на ваших кнопках: исследования, скорость, эволюция, энергия и производство в реальном времени (с графиками), планета, поезда UTLogistics; пауза, скорость, сохранение, снимок экрана и очередь исследований. Нужен мод Factorio «TouchDeck Bridge» (портал модов). Без параметров запуска, без сети: мод пишет JSON-файлы, плагин следит за ними.",
        "在按钮上显示 Factorio：实时显示研究、速度、进化度、电力和生产（含图表）、星球、UTLogistics 列车；暂停、调速、保存、截图和研究队列。需要 Factorio 模组“TouchDeck Bridge”（模组门户）。无需启动参数，无需网络：模组写入 JSON 文件，插件监视这些文件。"),
    "Restart Factorio – new mods are switched on automatically.": (
        "Redémarrez Factorio – les nouveaux mods sont activés automatiquement.",
        "Reinicia Factorio: los mods nuevos se activan automáticamente.",
        "Uruchom ponownie Factorio – nowe mody włączają się automatycznie.",
        "Reinicie o Factorio – mods novos são ativados automaticamente.",
        "Перезапустите Factorio – новые моды включаются автоматически.",
        "重启 Factorio——新模组会自动启用。"),
    "Folder of the mod files (empty = find automatically)": (
        "Dossier des fichiers du mod (vide = recherche automatique)", "Carpeta de los archivos del mod (vacío = buscar automáticamente)",
        "Folder plików moda (puste = szukaj automatycznie)", "Pasta dos arquivos do mod (vazio = procurar automaticamente)",
        "Папка файлов мода (пусто = искать автоматически)", "模组文件所在文件夹（留空 = 自动查找）"),
    "Check files every … ms (100–5000)": (
        "Vérifier les fichiers toutes les … ms (100–5000)", "Comprobar archivos cada … ms (100–5000)", "Sprawdzaj pliki co … ms (100–5000)",
        "Verificar arquivos a cada … ms (100–5000)", "Проверять файлы каждые … мс (100–5000)", "每隔 … 毫秒检查文件（100–5000）"),
    "No data for … seconds = not connected (2–60)": (
        "Pas de données depuis … secondes = déconnecté (2–60)", "Sin datos durante … segundos = desconectado (2–60)",
        "Brak danych przez … sekund = rozłączono (2–60)", "Sem dados por … segundos = desconectado (2–60)",
        "Нет данных … секунд = нет связи (2–60)", "… 秒无数据 = 未连接（2–60）"),
    "Without Factorio, check only every … ms (500–30000)": (
        "Sans Factorio, vérifier seulement toutes les … ms (500–30000)", "Sin Factorio, comprobar solo cada … ms (500–30000)",
        "Bez Factorio sprawdzaj tylko co … ms (500–30000)", "Sem o Factorio, verificar só a cada … ms (500–30000)",
        "Без Factorio проверять только каждые … мс (500–30000)", "未运行 Factorio 时，仅每隔 … 毫秒检查（500–30000）"),
    "Wait for the game's answer": ("Attendre la réponse du jeu", "Esperar la respuesta del juego", "Czekaj na odpowiedź gry",
                                   "Aguardar a resposta do jogo", "Ждать ответа игры", "等待游戏的回应"),
    "Command (empty = any)": ("Commande (vide = toutes)", "Orden (vacío = cualquiera)", "Polecenie (puste = dowolne)",
                              "Comando (vazio = qualquer)", "Команда (пусто = любая)", "命令（留空 = 任意）"),
    "Any": ("Toutes", "Cualquiera", "Dowolne", "Qualquer", "Любая", "任意"),
    "Pause (toggle)": ("Pause (bascule)", "Pausa (alternar)", "Pauza (przełącz)", "Pausa (alternar)", "Пауза (переключить)", "暂停（切换）"),
    "Speed": ("Vitesse", "Velocidad", "Prędkość", "Velocidade", "Скорость", "速度"),
    "Save game": ("Sauvegarder", "Guardar partida", "Zapisz grę", "Salvar jogo", "Сохранить игру", "保存游戏"),
    "Screenshot": ("Capture d'écran", "Captura de pantalla", "Zrzut ekranu", "Captura de tela", "Снимок экрана", "截图"),
    "Queue research": ("Ajouter une recherche", "Poner investigación en cola", "Dodaj badanie do kolejki", "Enfileirar pesquisa",
                       "Поставить исследование в очередь", "加入研究队列"),
    "Cancel research": ("Annuler la recherche", "Cancelar investigación", "Anuluj badanie", "Cancelar pesquisa",
                        "Отменить исследование", "取消研究"),
    "Back to the player": ("Retour au joueur", "Volver al jugador", "Wróć do gracza", "Voltar ao jogador", "Вернуться к игроку", "回到玩家"),
    "Write data again": ("Réécrire les données", "Volver a escribir datos", "Zapisz dane ponownie", "Gravar dados novamente",
                         "Записать данные заново", "重新写入数据"),
    "UTL manager": ("Gestionnaire UTL", "Gestor de UTL", "Menedżer UTL", "Gerenciador UTL", "Менеджер UTL", "UTL 管理器"),
    "Wait at most … seconds": ("Attendre au plus … secondes", "Esperar como máximo … segundos", "Czekaj najwyżej … sekund",
                               "Aguardar no máximo … segundos", "Ждать не более … секунд", "最多等待 … 秒"),
    "Production slot: choose item": ("Emplacement de production : choisir l'objet", "Posición de producción: elegir objeto",
                                     "Miejsce produkcji: wybierz przedmiot", "Posição de produção: escolher item",
                                     "Ячейка производства: выбрать предмет", "生产位置：选择物品"),
    "Slot (1–8)": ("Emplacement (1–8)", "Posición (1–8)", "Miejsce (1–8)", "Posição (1–8)", "Ячейка (1–8)", "位置（1–8）"),
    "What": ("Quoi", "Qué", "Co", "O quê", "Что", "操作"),
    "Next item": ("Objet suivant", "Objeto siguiente", "Następny przedmiot", "Próximo item", "Следующий предмет", "下一个物品"),
    "Previous item": ("Objet précédent", "Objeto anterior", "Poprzedni przedmiot", "Item anterior", "Предыдущий предмет", "上一个物品"),
    "Automatic (most produced)": ("Automatique (le plus produit)", "Automático (el más producido)", "Automatycznie (najwięcej produkowany)",
                                  "Automático (mais produzido)", "Автоматически (больше всего производится)", "自动（产量最高）"),
    "Choose by name": ("Choisir par nom", "Elegir por nombre", "Wybierz po nazwie", "Escolher pelo nome", "Выбрать по названию", "按名称选择"),
    "All slots automatic": ("Tous les emplacements automatiques", "Todas las posiciones automáticas", "Wszystkie miejsca automatycznie",
                            "Todas as posições automáticas", "Все ячейки автоматически", "全部位置自动"),
    "Name (in game language or internal)": ("Nom (langue du jeu ou interne)", "Nombre (idioma del juego o interno)",
                                            "Nazwa (w języku gry lub wewnętrzna)", "Nome (idioma do jogo ou interno)",
                                            "Название (на языке игры или внутреннее)", "名称（游戏语言或内部名称）"),
    "e.g. Iron plate or iron-plate": ("p. ex. Plaque de fer ou iron-plate", "p. ej. Placa de hierro o iron-plate",
                                      "np. Płyta żelaza lub iron-plate", "ex.: Placa de ferro ou iron-plate",
                                      "напр. Железная плита или iron-plate", "例如 铁板 或 iron-plate"),
    "UTLogistics: choose planet": ("UTLogistics : choisir la planète", "UTLogistics: elegir planeta", "UTLogistics: wybierz planetę",
                                   "UTLogistics: escolher planeta", "UTLogistics: выбрать планету", "UTLogistics：选择星球"),
    "Next planet": ("Planète suivante", "Planeta siguiente", "Następna planeta", "Próximo planeta", "Следующая планета", "下一个星球"),
    "Previous planet": ("Planète précédente", "Planeta anterior", "Poprzednia planeta", "Planeta anterior", "Предыдущая планета", "上一个星球"),
    "Automatic (where I am)": ("Automatique (là où je suis)", "Automático (donde estoy)", "Automatycznie (tam, gdzie jestem)",
                               "Automático (onde estou)", "Автоматически (где я нахожусь)", "自动（我所在的星球）"),
    "All planets": ("Toutes les planètes", "Todos los planetas", "Wszystkie planety", "Todos os planetas", "Все планеты", "所有星球"),
    "UTLogistics: open its page": ("UTLogistics : ouvrir sa page", "UTLogistics: abrir su página", "UTLogistics: otwórz jego stronę",
                                   "UTLogistics: abrir a página", "UTLogistics: открыть его страницу", "UTLogistics：打开其页面"),
    "UTLogistics: choose network slot": ("UTLogistics : choisir l'emplacement de réseau", "UTLogistics: elegir posición de red",
                                         "UTLogistics: wybierz miejsce sieci", "UTLogistics: escolher posição de rede",
                                         "UTLogistics: выбрать ячейку сети", "UTLogistics：选择网络位置"),
    "Next network": ("Réseau suivant", "Red siguiente", "Następna sieć", "Próxima rede", "Следующая сеть", "下一个网络"),
    "Previous network": ("Réseau précédent", "Red anterior", "Poprzednia sieć", "Rede anterior", "Предыдущая сеть", "上一个网络"),
    "Automatic (most stations)": ("Automatique (le plus de gares)", "Automático (más estaciones)", "Automatycznie (najwięcej stacji)",
                                  "Automático (mais estações)", "Автоматически (больше всего станций)", "自动（车站最多）"),
    "Research finished": ("Recherche terminée", "Investigación terminada", "Badanie ukończone", "Pesquisa concluída",
                          "Исследование завершено", "研究完成"),
    "Internal name (empty = any)": ("Nom interne (vide = toutes)", "Nombre interno (vacío = cualquiera)", "Nazwa wewnętrzna (puste = dowolne)",
                                    "Nome interno (vazio = qualquer)", "Внутреннее имя (пусто = любое)", "内部名称（留空 = 任意）"),
    "Research started": ("Recherche commencée", "Investigación iniciada", "Badanie rozpoczęte", "Pesquisa iniciada",
                         "Исследование начато", "研究开始"),
    "Rocket launched": ("Fusée lancée", "Cohete lanzado", "Rakieta wystrzelona", "Foguete lançado", "Ракета запущена", "火箭已发射"),
    "Player died": ("Joueur mort", "Jugador muerto", "Gracz zginął", "Jogador morreu", "Игрок погиб", "玩家死亡"),
    "Only me (ja) or others (nein), empty = all": ("Seulement moi (ja) ou les autres (nein), vide = tous",
                                                  "Solo yo (ja) u otros (nein), vacío = todos", "Tylko ja (ja) lub inni (nein), puste = wszyscy",
                                                  "Só eu (ja) ou outros (nein), vazio = todos", "Только я (ja) или другие (nein), пусто = все",
                                                  "仅自己（ja）或他人（nein），留空 = 全部"),
    "All": ("Tous", "Todos", "Wszyscy", "Todos", "Все", "全部"),
    "Me": ("Moi", "Yo", "Ja", "Eu", "Я", "自己"),
    "Others": ("Autres", "Otros", "Inni", "Outros", "Другие", "他人"),
    "Evolution passed a 10 % step": ("L'évolution a franchi un palier de 10 %", "La evolución superó un escalón del 10 %",
                                     "Ewolucja przekroczyła próg 10 %", "A evolução passou de um degrau de 10 %",
                                     "Эволюция прошла порог 10 %", "进化度跨过 10% 档位"),
    "Command answered by the game": ("Commande confirmée par le jeu", "Orden respondida por el juego", "Gra odpowiedziała na polecenie",
                                     "Comando respondido pelo jogo", "Игра ответила на команду", "游戏已回应命令"),
    "Result (empty = any)": ("Résultat (vide = tous)", "Resultado (vacío = cualquiera)", "Wynik (puste = dowolny)",
                             "Resultado (vazio = qualquer)", "Результат (пусто = любой)", "结果（留空 = 任意）"),
    "Done": ("Fait", "Hecho", "Wykonano", "Feito", "Выполнено", "已完成"),
    "Failed": ("Échec", "Fallido", "Nieudane", "Falhou", "Ошибка", "失败"),
    "Game connected": ("Jeu connecté", "Juego conectado", "Gra połączona", "Jogo conectado", "Игра подключена", "游戏已连接"),
    "Game disconnected": ("Jeu déconnecté", "Juego desconectado", "Gra rozłączona", "Jogo desconectado", "Игра отключена", "游戏已断开"),
    "UTLogistics: new alert (full text)": ("UTLogistics : nouvelle alerte (texte complet)", "UTLogistics: nuevo aviso (texto completo)",
                                           "UTLogistics: nowe ostrzeżenie (pełny tekst)", "UTLogistics: novo alerta (texto completo)",
                                           "UTLogistics: новое предупреждение (полный текст)", "UTLogistics：新警报（完整文本）"),
    "UTLogistics: request waiting without a train": ("UTLogistics : demande en attente sans train", "UTLogistics: solicitud esperando sin tren",
                                                     "UTLogistics: zapotrzebowanie czeka bez pociągu", "UTLogistics: pedido aguardando sem trem",
                                                     "UTLogistics: запрос ждёт без поезда", "UTLogistics：请求在等待且无列车"),
    "Research with progress": ("Recherche avec progression", "Investigación con progreso", "Badanie z postępem", "Pesquisa com progresso",
                               "Исследование с прогрессом", "研究及进度"),
    "Connection and pause": ("Connexion et pause", "Conexión y pausa", "Połączenie i pauza", "Conexão e pausa", "Связь и пауза", "连接与暂停"),
    "Game speed": ("Vitesse du jeu", "Velocidad del juego", "Prędkość gry", "Velocidade do jogo", "Скорость игры", "游戏速度"),
    "Evolution (%, graph)": ("Évolution (%, graphique)", "Evolución (%, gráfico)", "Ewolucja (%, wykres)", "Evolução (%, gráfico)",
                             "Эволюция (%, график)", "进化度（%，图表）"),
    "Power production (MW, graph by source)": ("Production électrique (MW, graphique par source)", "Producción eléctrica (MW, gráfico por fuente)",
                                               "Produkcja prądu (MW, wykres wg źródła)", "Produção de energia (MW, gráfico por fonte)",
                                               "Выработка энергии (МВт, график по источникам)", "发电量（MW，按来源的图表）"),
    "Power consumption (MW, graph by consumer)": ("Consommation électrique (MW, graphique par consommateur)",
                                                  "Consumo eléctrico (MW, gráfico por consumidor)", "Zużycie prądu (MW, wykres wg odbiorcy)",
                                                  "Consumo de energia (MW, gráfico por consumidor)", "Потребление энергии (МВт, график по потребителям)",
                                                  "耗电量（MW，按耗电者的图表）"),
    "UTLogistics: trains idle / on the way (graph)": ("UTLogistics : trains libres / en route (graphique)", "UTLogistics: trenes libres / en camino (gráfico)",
                                                      "UTLogistics: pociągi wolne / w drodze (wykres)", "UTLogistics: trens livres / a caminho (gráfico)",
                                                      "UTLogistics: поезда свободны / в пути (график)", "UTLogistics：空闲/途中列车（图表）"),
    "UTLogistics: alerts (last 10 min)": ("UTLogistics : alertes (10 dernières min)", "UTLogistics: avisos (últimos 10 min)",
                                          "UTLogistics: ostrzeżenia (ostatnie 10 min)", "UTLogistics: alertas (últimos 10 min)",
                                          "UTLogistics: предупреждения (последние 10 мин)", "UTLogistics：警报（最近 10 分钟）"),
    "UTLogistics: goods delivered per hour (graph by good)": ("UTLogistics : marchandises livrées par heure (graphique par marchandise)",
                                                              "UTLogistics: mercancías entregadas por hora (gráfico por mercancía)",
                                                              "UTLogistics: dostarczone towary na godzinę (wykres wg towaru)",
                                                              "UTLogistics: mercadorias entregues por hora (gráfico por mercadoria)",
                                                              "UTLogistics: доставлено товаров в час (график по товарам)",
                                                              "UTLogistics：每小时送达货物（按货物的图表）"),
    "UTLogistics: deliveries per hour (graph)": ("UTLogistics : livraisons par heure (graphique)", "UTLogistics: entregas por hora (gráfico)",
                                                 "UTLogistics: dostawy na godzinę (wykres)", "UTLogistics: entregas por hora (gráfico)",
                                                 "UTLogistics: доставки в час (график)", "UTLogistics：每小时送货次数（图表）"),
    "UTLogistics: requests without a train": ("UTLogistics : demandes sans train", "UTLogistics: solicitudes sin tren",
                                              "UTLogistics: zapotrzebowania bez pociągu", "UTLogistics: pedidos sem trem",
                                              "UTLogistics: запросы без поезда", "UTLogistics：无列车的请求"),
}

# Nummerierte Texte (Plätze 1–8)
PATTERNS = [
    (r"Production slot (\d) \(per minute, graph\)",
     ("Emplacement de production {} (par minute, graphique)", "Posición de producción {} (por minuto, gráfico)",
      "Miejsce produkcji {} (na minutę, wykres)", "Posição de produção {} (por minuto, gráfico)",
      "Ячейка производства {} (в минуту, график)", "生产位置 {}（每分钟，图表）")),
    (r"UTLogistics: pinned station (\d) \(trains, graph\)",
     ("UTLogistics : gare épinglée {} (trains, graphique)", "UTLogistics: estación fijada {} (trenes, gráfico)",
      "UTLogistics: przypięta stacja {} (pociągi, wykres)", "UTLogistics: estação fixada {} (trens, gráfico)",
      "UTLogistics: закреплённая станция {} (поезда, график)", "UTLogistics：固定车站 {}（列车，图表）")),
    (r"UTLogistics: network slot (\d) \(graph\)",
     ("UTLogistics : emplacement de réseau {} (graphique)", "UTLogistics: posición de red {} (gráfico)",
      "UTLogistics: miejsce sieci {} (wykres)", "UTLogistics: posição de rede {} (gráfico)",
      "UTLogistics: ячейка сети {} (график)", "UTLogistics：网络位置 {}（图表）")),
]


def translate(en):
    if en in TABLE:
        return TABLE[en]
    for pattern, texts in PATTERNS:
        m = re.fullmatch(pattern, en)
        if m:
            return tuple(t.format(m.group(1)) for t in texts)
    return None


def main():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugin.json")
    data = json.load(open(path, encoding="utf-8"))
    missing = set()

    def walk(v):
        if isinstance(v, dict):
            if "en" in v and "de" in v and all(isinstance(x, str) for x in v.values()):
                texts = translate(v["en"])
                if texts is None:
                    missing.add(v["en"])
                else:
                    for lang, text in zip(LANGS, texts):
                        v[lang] = text
                return
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    walk(data)
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for en in sorted(missing):
        print("ohne Übersetzung:", en)
    print("plugin.json übersetzt" + (f" ({len(missing)} Texte fehlen)" if missing else ""))


if __name__ == "__main__":
    main()
