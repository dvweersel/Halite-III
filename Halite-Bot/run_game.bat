call activate halite
rem halite.exe --replay-directory replays/ --width 32 --height 32 --results-as-json --no-timeout "python MyBot.py" "python ..\\Halite-Bot-v13\\MyBot-v13.py" "python C:\\Users\Administrator\\Documents\\Halite\\Halite-III\\Halite-Bot-v11\\MyBot-v11.py" "python C:\\Users\Administrator\\Documents\\Halite\\Halite-III\\Halite-Bot\\MyBot.py"
halite.exe --replay-directory replays/ --width 64 --height 64 "pypy3 MyBot.py" "pypy3 ..\\Halite-Bot-dev\\MyBot.pypy"
call deactivate