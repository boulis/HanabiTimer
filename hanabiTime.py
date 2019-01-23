import readchar
import time
import datetime
import csv
import json
from argparse import ArgumentParser

class TerminalFormatting:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class HanabiTimer:

    def __init__(self, players=['Evi', 'Giorgos', 'Thanassis'], 
                 clues=8, multi_key_interval=0.2, multicolor=False):
        # mapping keys to actions
        self.actions = {
            '1': 'tell', 
            '2': 'discard', 
            '3': 'play', 
            '4': 'pause', 
            '5': 'undo',
            'x': 'exit'
        }
        # mapping multiple press keys to actions
        self.multi_key_actions = { '23': 'play 5'}

        self.players = players
        self.current_player_index = 0
        self.current_player = players[0]
        self.clues = clues
        self.multi_key_interval = multi_key_interval
        self.fives_to_play = 6 if multicolor else 5

        self.start = None
        self.game_paused = False
        self.pause_start_time = None
        self.pause_duration = 0
        self.undo_duration = 0
        self.previous_time = None
        self.previous_pressed_key = None
        self.moves = [['Name', 'Action', 'Duration']]

    def next_player(self):
        if self.current_player_index == len(self.players) - 1 :
            self.current_player_index = 0
        else:
            self.current_player_index += 1
        return self.players[self.current_player_index]

    def prev_player(self):
        if self.current_player_index == 0 :
            self.current_player_index = len(self.players) - 1
        else:
            self.current_player_index -= 1
        return self.players[self.current_player_index]


    def record_and_proceed(self, key, current_time, action= None, diff=None):
        if not diff:
            action_str = 'starts game by telling'.ljust(30)
            move_duration = 0
        else:
            move_duration = diff - self.pause_duration + self.undone_moves_duration
            action_str = 'took {:5.1f} secs to {}'.format(move_duration, action).ljust(30)

        clues_str = TerminalFormatting.BOLD + \
                    (TerminalFormatting.GREEN if self.clues > 2 else TerminalFormatting.RED) + \
                    str(self.clues) + TerminalFormatting.ENDC 
        print(self.current_player.ljust(10), action_str, '\t', ' We have', clues_str, 'clues')
        self.moves.append([ self.current_player, action, move_duration ])
        self.previous_pressed_key = key
        self.current_player = self.next_player()
        self.previous_time = current_time
        self.pause_duration = 0
        self.undone_moves_duration = 0


    def run(self):
        while True:
            key = readchar.readchar()
            if key not in self.actions: 
                print('Valid keys are:', self.actions)
                continue
            if self.actions[key] == 'exit': break

            if self.game_paused and self.actions[key] != 'pause':
                print('\a   *** Game paused. Hit pause button to continue ***')
                continue
            
            # any other key action we record the time
            current_time = time.time()

            # any key press other than exist, starts the game (assumimg telling clue)
            if self.start is None:
                # begin the game
                self.start = current_time
                self.clues -= 1
                self.record_and_proceed(key, current_time, 'tell')
                # go to the next key press
                continue 
        

            diff = current_time - self.previous_time
            # first check if we have multiple keys pressed
            if diff < self.multi_key_interval:
                for multi_keys in self.multi_key_actions:
                    if key in multi_keys and self.previous_pressed_key in multi_keys:
                        if self.multi_key_actions[multi_keys] == 'play 5':
                            # add an extra clue, but only if the previous (almost synchronous)
                            # key press was 'discard'. Otherwise the extra clue was already added.
                            if self.moves[-1][1] != 'discard':
                                self.clues = 8 if self.clues > 7 else self.clues + 1
                            self.fives_to_play -= 1
                        # roll back the recording of the previous move
                        # keep the duration of the previous move before deleting it
                        diff = self.moves[-1][2]
                        del self.moves[-1]
                        self.current_player = self.prev_player()
                        self.record_and_proceed(key, current_time, 
                                self.multi_key_actions[multi_keys], diff
                        )
                # check if the game is over
                if self.fives_to_play == 0: break
                # else go to the next key press
                continue 

            # then we check single key presses

            if self.actions[key] == 'tell':
                if self.clues == 0:
                    # print error together with sound alert ('\a' is the bell char)
                    print('\a\a\a   *** ILLEGAL MOVE - Telling with no clues left ***')
                    continue
                self.clues -= 1
                self.record_and_proceed(key, current_time, self.actions[key], diff)
                continue

            if self.actions[key] == 'play':
                self.record_and_proceed(key, current_time, self.actions[key], diff)
                continue

            if self.actions[key] == 'discard':
                self.clues = 8 if self.clues == 8 else self.clues + 1
                self.record_and_proceed(key, current_time, self.actions[key], diff)
                continue

            if self.actions[key] == 'pause':
                if self.game_paused:
                    self.game_paused = False
                    print('*** Game Un-paused ***')
                    self.pause_duration += current_time - self.pause_start_time
                    continue
                else: 
                    self.game_paused = True
                    print('*** Game Paused ***')
                    self.pause_start_time = current_time
                    continue
                
            if self.actions[key] == 'undo':
                self.undone_moves_duration += self.moves[-1][2]
                # correct the number of clues, based on what the undone move is
                if self.moves[-1][1] == 'discard' or self.moves[-1][1] == 'play 5':
                    self.clues -= 1
                if self.moves[-1][1] == 'tell':
                    self.clues += 1
                # remove the move from our record
                del self.moves[-1]
                self.current_player = self.prev_player()
                print('*** Last move undone ***')
                continue

        # Finally write all the moves to a file, and show the total time
        if self.start is not None:
            timestamp = time.strftime('%Y-%m-%d_%H_%M_%S_%a',time.localtime(self.start))
            filename = 'hanabi-{}{}.csv'.format(timestamp, '-FAIL' if self.fives_to_play > 0 else '')
            with open(filename,'w') as resultFile:
                wr = csv.writer(resultFile, dialect='excel')
                wr.writerows(self.moves)

            print('\nTotal game time:',
                datetime.timedelta(seconds=sum([m[2] for m in self.moves[1:]])), '\n')

            stats = {}
            for player in self.players:
                player_moves = [m for m in self.moves[1:] if m[0] == player]
                print(player.ljust(10),' - Total time:', 
                    datetime.timedelta(seconds=sum([m[2] for m in player_moves])))
                stats[player] = {}
                for m in player_moves:
                    if m[1] in stats[player]:
                        stats[player][m[1]] += 1
                    else:
                        stats[player][m[1]] = 1
            print(json.dumps(stats, sort_keys=True, indent=4))

if __name__ == '__main__':
    h = HanabiTimer()
    h.run()
