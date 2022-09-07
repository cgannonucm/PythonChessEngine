from board import *
from moveengine import *

class ChessBoard:

    move_engine:MoveEngine = None

    @property
    def board(self)->Board:
        return self.move_engine.board

    @property
    def turn(self)->Board:
        return self.move_engine.turn
    
    @property
    def legal_moves(self)->list[Move]:
        return self.move_engine.get_moves()

    @property
    def psuedo_legal_moves(self)->list[Move]:
        return self.move_engine.get_moves_pseudo_legal()
    

    def __init__(self) -> None:
        pass