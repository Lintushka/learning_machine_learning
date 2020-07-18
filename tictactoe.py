game = [[0, 0, 0],
        [0, 0, 0],
        [0, 0, 0], ]


def game_board(game_map, player=0, row=0, column=0, just_display=False):
    print('   a  b  c')
    if not just_display:
        game_map[row][column] = player
    for count, row in enumerate(game_map):
        print(count, row)
    return game_map


game = game_board(game, just_display=True)
game = game_board(game, 1, 2, 1)
#game[0][1] = 1

#game_board(1, 2, 0)
