from shutil import move
import pygame, sys
from pygame.locals import *
import math
import time
from pseudomoves import *
from moveengine import *
from copy import deepcopy


class ChessGUI:

    moveengine = MoveEngine(BoardIO.from_fen(FEN.POS_5),MoveCache())

    @property
    def board(self):
        return self.moveengine.board

    rendering = True

    COLORBLACK = (0, 0, 0)
    COLORWHITE = (255, 255, 255)
    COLORBROWN = (181,136,99)
    COLORLIGHTBROWN = (240,217,181)
    COLORRUST = (237,99,101)
    COLORBLUE = (71,170,209)
    COLORPURPLE = (148,80,209)

    offset = None


    BOARDLENGTH = 8 * 100
    FPS = 60

    COLORSQUAREWHITE = COLORLIGHTBROWN
    COLORSQUAREBLACK = COLORBROWN

    #Sprites
    sprites:dict[int,pygame.Surface] = None
    sprite_path = "../sprites/chessmen/default"
    sprite_path_b_pawn = "b_pawn_png_128px.png"
    sprite_path_b_knight = "b_knight_png_128px.png"
    sprite_path_b_bishop = "b_bishop_png_128px.png"
    sprite_path_b_rook = "b_rook_png_128px.png"
    sprite_path_b_king = "b_king_png_128px.png"
    sprite_path_b_queen = "b_queen_png_128px.png"

    sprite_path_w_pawn = "w_pawn_png_128px.png"
    sprite_path_w_knight = "w_knight_png_128px.png"
    sprite_path_w_bishop = "w_bishop_png_128px.png"
    sprite_path_w_rook = "w_rook_png_128px.png"
    sprite_path_w_king = "w_king_png_128px.png"
    sprite_path_w_queen = "w_queen_png_128px.png"


    CLOCK = pygame.time.Clock()

    TEXTWIDTH = 175
    

    __moves:list[Move] = []
    __draged_piece:tuple[float,float] = None
    __selected_piece:int = None

    __movestack:list[MoveInstruction] = []


    __cursor_pos = None

    def __init__(self) -> None:
        self.DISPLAYSURF = pygame.display.set_mode((self.BOARDLENGTH + self.TEXTWIDTH,self.BOARDLENGTH))
        self.cache = MoveCache()
        
        pygame.init()
        self.load_sprites()
    
    def load_sprites(self):
        def get_path(name) -> str:
            return f"{self.sprite_path}/{name}"

        self.sprites = {}
        sprites = self.sprites

        sprites[PieceType.PAWN] = (pygame.image.load(get_path(self.sprite_path_w_pawn)),pygame.image.load(get_path(self.sprite_path_b_pawn)))
        sprites[PieceType.KNIGHT] = (pygame.image.load(get_path(self.sprite_path_w_knight)),pygame.image.load(get_path(self.sprite_path_b_knight)))
        sprites[PieceType.BISHOP] = (pygame.image.load(get_path(self.sprite_path_w_bishop)),pygame.image.load(get_path(self.sprite_path_b_bishop)))
        sprites[PieceType.ROOK] = (pygame.image.load(get_path(self.sprite_path_w_rook)),pygame.image.load(get_path(self.sprite_path_b_rook)))
        sprites[PieceType.QUEEN] = (pygame.image.load(get_path(self.sprite_path_w_queen)),pygame.image.load(get_path(self.sprite_path_b_queen)))
        sprites[PieceType.KING] = (pygame.image.load(get_path(self.sprite_path_w_king)),pygame.image.load(get_path(self.sprite_path_b_king)))

        
    def render_loop(self):
        while self.rendering:
            self.DISPLAYSURF.fill(self.COLORBLACK)
            self.__draw()
            pygame.display.update()
 
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.select_piece(event.pos)
                if event.type == MOUSEBUTTONUP:
                    if event.button == 1:
                        self.unselect_piece(event.pos)
                if event.type == MOUSEMOTION:
                    self.__cursor_pos = event.pos
                if event.type == KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        self.undo()
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_x:
                        self.rendering = False
                        pygame.quit()
                        
   
            self.CLOCK.tick(self.FPS)
    
    def undo(self):
        if len(self.moveengine.move_stack) == 0: return
        self.moveengine.unmove()

    def get_square_cursor_on(self,cursor_pos:tuple[float,float])->tuple[int,int]:
        (x_px,y_px) = cursor_pos

        length_px = self.__get_square_length()

        x = math.floor(x_px/length_px)
        y = math.floor(y_px/length_px)

        return (x,y)

    def __select_piece(self,pos):
        #Fix sphagetti code

        self.__moves = self.moveengine.get_moves_piece(self.__selected_piece)


    def select_piece(self,cursor_pos):
        pos = self.get_square_cursor_on(cursor_pos)
        piece_pos = self.__get_px_coordinates(pos)

        self.offset = (piece_pos[0] - cursor_pos[0],piece_pos[1] - cursor_pos[1])

        bit_pos = Bitboard.get_pos(*pos)
        if not self.board.occupied(bit_pos): return 

        if self.board.turn != self.board.get_color(bit_pos): return

        self.__draged_piece = bit_pos
        
        self.__select_piece(bit_pos)

        self.__selected_piece = bit_pos

    def move(self,pos_from:tuple[int,int],pos_to:tuple[int,int]):
        """Attempts to move piece from one position to another"""
        #Attempt to move piece
        self.__select_piece(self.__selected_piece)
        
        for _move in self.__moves:
            if _move.pos_to == pos_to:
                self.moveengine.move(_move)
                return True

        return False
        


        #Update display string

    def unselect_piece(self,cursor_pos):
        pos_to = self.get_square_cursor_on(cursor_pos)

        #Move piece
        sucess = self.move(self.__draged_piece,Bitboard.get_pos(*pos_to))

        #self.__moves = self.gamestate.select(pos_to)
        if sucess: self.__moves = []

        #Deselct piece
        self.__draged_piece = None



    def __get_square_length(self):
        square_length_count = self.board.BOARDSQUARELENGTH
        return self.BOARDLENGTH / square_length_count

    def __get_px_coordinates(self,coords:tuple[int,int])->tuple[float,float]:
        square_length = self.__get_square_length()

        return (coords[0] * square_length,coords[1] * square_length)


    def __draw_square(self,pos:tuple[float,float],color:tuple[float,float,float]):
        (x_px,y_px) = self.__get_px_coordinates(pos)
        
        square_length_count = self.board.BOARDSQUARELENGTH
        square_lenght = self.BOARDLENGTH / square_length_count

        pygame.draw.rect(self.DISPLAYSURF,color,(x_px,y_px,square_lenght,square_lenght))

    def __draw_board(self)->None:
        """Draws chess board squares"""
        cwite = self.COLORSQUAREWHITE
        cblack = self.COLORSQUAREBLACK

        square_length_count = self.board.BOARDSQUARELENGTH

        for x in range(square_length_count):
            for y in range(square_length_count):

                color = cwite if (x + y) % 2 == 0 else cblack

                self.__draw_square((x,y),color)

    def __draw_piece(self,pos_px:tuple[float,float],piece_type:int,color:int)->None:
        DISPLAYSURF = self.DISPLAYSURF
        
        length = self.__get_square_length()
            
        sprite = self.sprites[piece_type][color]
            
        sprite_to_draw = pygame.transform.scale(sprite,(length,length))
        DISPLAYSURF.blit(sprite_to_draw,(*pos_px,length,length))


    def __draw_pieces(self)->None:
        """Draw all pieces on board"""
        chessboard = self.board
        DISPLAYSURF = self.DISPLAYSURF

        len = self.__get_square_length()

        for color in range(2):
            for piece_type in range(6):
                list_pos = self.board.get_list_pos(color,piece_type)
                locations = self.board.locations[list_pos]
                for pos_bit in locations:
                    #Do not draw piece here if it is being dragged and dropped
                    if pos_bit == self.__draged_piece: continue

                    pos = (Bitboard.get_x(pos_bit),Bitboard.get_y(pos_bit))

                    pos_px = self.__get_px_coordinates(pos)

                    self.__draw_piece(pos_px,piece_type,color)

    def __draw_drag_and_drop(self):

        offset = self.offset

        coords_from = self.__draged_piece

        if coords_from == None: return

        c_board = self.board

        piece = c_board.get(coords_from)

        (x,y) = self.__cursor_pos
        self.__draw_piece((x + offset[0],y + offset[1]),c_board.get_piece_type(self.__selected_piece,c_board.turn),c_board.turn)

            

    def __draw_moves(self):
        """Draws possible moves"""
        for move in self.__moves:
            color = self.COLORRUST
            self.__draw_square(Bitboard.get_pos_2d(move.pos_to),color)
    

    check_str = "Check!"
    checkmate_str = "Checkmate!" 
    stalemate_str = "Stalemate!"

    display_str = ""

    def __update_text(self):
        return
        gs = self.gamestate

        if gs.checkmate:
            self.display_str = self.checkmate_str
        elif gs.stalemate:
            self.display_str = self.stalemate_str
        elif gs.in_check:
            self.display_str = self.check_str
        else:
            self.display_str = ""

    def __render_text(self):
        self.__update_text()
        font = pygame.font.SysFont('timesnewroman',32)
        check_txt = font.render(self.display_str,True,self.COLORWHITE)
        text_rect = check_txt.get_rect()
        text_rect.center = (self.BOARDLENGTH + self.TEXTWIDTH // 2, self.BOARDLENGTH // 2)

        self.DISPLAYSURF.blit(check_txt,text_rect)

    def __draw(self):
        """Draws chess game"""
        self.__draw_board()
        self.__draw_moves()
        self.__draw_pieces()
        self.__draw_drag_and_drop()
        self.__render_text()
        

gui = ChessGUI()
gui.render_loop()
