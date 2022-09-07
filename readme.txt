Running
--------------------------------------------------
To run simply run the run.bat file
--------------------------------------------------


Help
--------------------------------------------------
For a list of commands type "help"
For help with a sepecific command type "help *command*"
with *command* replaced with the command that you need help with
--------------------------------------------------


Playing against computer
--------------------------------------------------
Warning: the computer opponent is actually kinda ok at chess. It kicks my butt
everytime. I am really bad at chess thought. So your milage may very.


To play against cpu first toggle game mode on using gamemode command
Note no need to type (chess) to execute commands, just type command name

Example
--------------
(chess) gamemode
Gamemode toggled on!
--------------

Then select piece you want to move.
Example select pawn on a2 to move:

Example
--------------
(chess) select a2
0: Move object: Move p from a2 to a3
1: Move object: Move p from a2 to a4
--------------

Finally, choose your move
For example move pawn on a2 to a4

Example
---------------
select 1
--------------

Your move will be processed and the
computer will automatically play it's move!

All together the final output should look like this

Welcome to unnamed chess engine console
Note 50 move rule and draw by repitition have not yet been implemented
Type "help" for help or "help" "Command" for help with a specific command
(chess)gamemode
Gamemode toggled on!
(chess)select a2
0: Move object: Move p from a2 to a3
1: Move object: Move p from a2 to a4
(chess)move 1
+----+----+----+----+----+----+----+----+
| r  | n  | b  | q  | k  | b  | n  | r  |  8
+----+----+----+----+----+----+----+----+
| p  | p  | p  | p  | p  | p  | p  | p  |  7
+----+----+----+----+----+----+----+----+
|    |    |    |    |    |    |    |    |  6
+----+----+----+----+----+----+----+----+
|    |    |    |    |    |    |    |    |  5
+----+----+----+----+----+----+----+----+
| P  |    |    |    |    |    |    |    |  4
+----+----+----+----+----+----+----+----+
|    |    |    |    |    |    |    |    |  3
+----+----+----+----+----+----+----+----+
|    | P  | P  | P  | P  | P  | P  | P  |  2
+----+----+----+----+----+----+----+----+
| R  | N  | B  | Q  | K  | B  | N  | R  |  1
+----+----+----+----+----+----+----+----+
  a    b    c    d    e    f    g    h
Evaluation 5, move: Move object: Move n from b8 to c6
+----+----+----+----+----+----+----+----+
| r  |    | b  | q  | k  | b  | n  | r  |  8
+----+----+----+----+----+----+----+----+
| p  | p  | p  | p  | p  | p  | p  | p  |  7
+----+----+----+----+----+----+----+----+
|    |    | n  |    |    |    |    |    |  6
+----+----+----+----+----+----+----+----+
|    |    |    |    |    |    |    |    |  5
+----+----+----+----+----+----+----+----+
| P  |    |    |    |    |    |    |    |  4
+----+----+----+----+----+----+----+----+
|    |    |    |    |    |    |    |    |  3
+----+----+----+----+----+----+----+----+
|    | P  | P  | P  | P  | P  | P  | P  |  2
+----+----+----+----+----+----+----+----+
| R  | N  | B  | Q  | K  | B  | N  | R  |  1
+----+----+----+----+----+----+----+----+
  a    b    c    d    e    f    g    h
(chess)
--------------------------------------------------

RESETING
---------------------------
to reset simply use reset command

Example
---------------
(chess)reset
---------------

