with Ada.Text_IO;
use Ada.Text_IO;

procedure Main is
   -- Task Nave
   task type Nave is
      entry Start (posHor : Integer);
      entry ObtenerPos (posHor : out Integer);
      entry ObtenerEstado (estado : out Boolean);
      entry Movimiento (valor : Integer);
      entry Terminar;
      entry TerminarJuego;
   end Nave;

   task body Nave is
      posHorNave : Integer;
      estaActivo : Boolean := True;
      termineJuego : Boolean := False;
   begin
      while termineJuego = False loop
         select
            accept Start (posHor : Integer) do
               posHorNave := posHor;
            end Start;
         or
            accept ObtenerPos (posHor : out Integer) do
               posHor := posHorNave;
            end ObtenerPos;
         or
            accept ObtenerEstado (estado : out Boolean) do
               estado := estaActivo;
            end ObtenerEstado;
         or
            accept Movimiento (valor : Integer) do
               posHorNave := posHorNave + valor;
            end Movimiento;
         or
            accept Terminar do
               estaActivo := False;
            end Terminar;
         or
            accept TerminarJuego do
               termineJuego := True;
            end TerminarJuego;
         end select;
      end loop;
   end Nave;

   --Task Bala
   task type Bala is
      entry Start (posHor : Integer);
      entry ObtenerPos (posVer : out Integer; posHor : out Integer);
      entry ObtenerEstado (estado : out Boolean);
      entry Movimiento;
      entry ValidoColision (unaNave : Nave);
      entry Terminar;
      entry TerminarJuego;
   end Bala;

   task body Bala is
      posVerBala : Integer;
      posHorBala : Integer;
      estaActiva : Boolean := False;
      termineJuego : Boolean := False;
      posAux : Integer;
      estadoNave : Boolean;
   begin
      while termineJuego = False loop
         select
            accept Start (posHor : Integer) do
               posVerBala := 22; -- Comienza en el pixel luego del cañon
               posHorBala := posHor;
               estaActiva := True;
            end Start;
         or
            accept ObtenerPos (posVer : out Integer; posHor : out Integer) do
               posVer := posVerBala;
               posHor := posHorBala;
            end ObtenerPos;
         or
            accept ObtenerEstado (estado : out Boolean) do
               estado := estaActiva;
            end ObtenerEstado;
         or
            accept Movimiento do
               posVerBala := posVerBala - 1;
            end Movimiento;
         or
            accept ValidoColision (unaNave : Nave) do
               unaNave.ObtenerEstado(estadoNave);
               if estadoNave = True then
                  if posVerBala = 1 or posVerBala = 2 or posVerBala = 5 or posVerBala = 6 then
                     unaNave.ObtenerPos(posAux);
                     if posVerBala = 1 or posVerBala = 5 then
                        if posHorBala = posAux or posHorBala = posAux + 1 or posHorBala = posAux + 2 then
                           estaActiva := False;
                           unaNave.Terminar;
                        end if;
                     else
                        if posHorBala = posAux + 1 then
                           estaActiva := False;
                           unaNave.Terminar;
                        end if;
                     end if;
                  end if;
               end if;
            end ValidoColision;
         or
            accept Terminar do
               estaActiva := False;
            end Terminar;
         or
            accept TerminarJuego do
               termineJuego := True;
            end TerminarJuego;
         end select;
      end loop;
   end Bala;

   -- Task Entrada y Protected Object EntradaGuardada
   -- El Protected Object tomado del libro Introduction to Ada
   protected EntradaGuardada is
      procedure Guardar (valorEntrada : Character);
      function Obtener return Character;
   private
      entrada : Character := ' ';
   end EntradaGuardada;

   protected body EntradaGuardada is
      procedure Guardar (valorEntrada : Character) is
      begin
         entrada := valorEntrada;
      end Guardar;

      function Obtener return Character is
      begin
         return entrada;
      end Obtener;
   end EntradaGuardada;

   task Entrada;
   task body Entrada is
      entrada : Character := ' ';
   begin
      loop
         Get_Immediate(entrada); -- Uso Get_Immediate para que no espere el Enter (Fuente: Claude)
         if entrada = 'a' or entrada = 'A' or entrada = 'D' or entrada = 'd' or entrada = 'w' or entrada = 'W' then
            if entrada = 'a' or entrada = 'A' then
               EntradaGuardada.Guardar('A');
            elsif entrada = 'd' or entrada = 'D' then
               EntradaGuardada.Guardar('D');
            else
               EntradaGuardada.Guardar('W');
            end if;
         end if;

      end loop;
   end Entrada;

   -- Procedimiento para limpiar la consola
   -- Fuente: https://www.reddit.com/r/ada/comments/8ad5xm/clearing_the_console/
   procedure Clear_Screen is
      Control_Preamble : constant Character := Character'Val (8#33#); -- '\033'
      Clear_Screen_Code: constant String    := "[2J";
      Home_Cursor_Code : constant String    := "[;H";

      Clear_Screen_Sequence: constant String
        := Control_Preamble & Clear_Screen_Code &
           Control_Preamble & Home_Cursor_Code;

   begin
      Put_Line(Clear_Screen_Sequence);
   end Clear_Screen;

   -- Variables utilizadas
   misNaves : array (1 .. 17) of Nave;
   misBalas : array(1 .. 23) of Bala;
   naveJugador : Nave;
   posVer : Integer;
   posHor : Integer;
   posAnt : Integer;
   posAux : Integer;
   posBala : Integer;
   desde : Integer;
   hasta : Integer;
   muevoDer : Boolean := True;
   siguienteDer : Boolean := True;
   entradaValor : Character;
   posUltimaBala : Integer := 0;
   estadoBala : Boolean;
   estadoNave : Boolean;
   hayBala : Boolean;
   termine : Boolean := False;
begin
   -- Inicializo naves
   posHor := 7;
   for nave in misNaves'Range loop
      misNaves (nave).Start(posHor);
      if nave = 9 then -- Cambio a segunda fila de naves enemigas
         posHor := 11;
      else
         posHor := posHor + 8;
      end if;
   end loop;
   -- Inicializo nave del jugador
   naveJugador.Start(40);

   -- Loop principal del juego
   while termine = False loop

      -- Muevo nave del jugador o disparo bala
      entradaValor := EntradaGuardada.Obtener;
      naveJugador.ObtenerPos(posHor);
      if entradaValor = 'A' and posHor > 1 then
         naveJugador.Movimiento(-1);
      elsif entradaValor = 'D' and posHor < 78 then
         naveJugador.Movimiento(1);
      elsif entradaValor = 'W' then
         posUltimaBala := posUltimaBala + 1;
         if posUltimaBala = 24 then
            posUltimaBala := 1;
         end if;
         misBalas (posUltimaBala).Start(posHor + 1);
      end if;
      EntradaGuardada.Guardar(' '); -- Quito el valor para que solo se mueva de nuevo si se presiona otra vez una tecla

      -- Muevo naves enemigas
      termine := True;
      for nave in misNaves'Range loop
         misNaves(nave).ObtenerEstado(estadoNave);
         if estadoNave = True then
            termine := False;
            if muevoDer = True then
               misNaves(nave).Movimiento(1);
            else
               misNaves(nave).Movimiento(-1);
            end if;
            misNaves(nave).ObtenerPos(posHor);
            if posHor = 78 then -- Una nave ya llego hasta el borde derecho
               siguienteDer := False;
            elsif posHor = 1 then -- Una nave ya llego hasta el borde izquierdo
               siguienteDer := True;
            end if;
         end if;
      end loop;
      muevoDer := siguienteDer;

      -- Muevo todas las balas una posicion y chequeo colisiones
      for bala in misBalas'Range loop
         misBalas(bala).ObtenerEstado(estadoBala);
         if estadoBala = True and (entradaValor /= 'W' or (entradaValor = 'W' and bala /= posUltimaBala)) then

            misBalas(bala).Movimiento;
            misBalas(bala).ObtenerPos(posVer, posHor);
            if posVer = 0 then
               misBalas(bala).Terminar;
               null;
            elsif posVer = 1 or posVer = 2 or posVer = 5 or posVer = 6 then
               if posVer = 1 or posVer = 2 then
                  desde := 1;
                  hasta := 9;
               else
                  desde := 10;
                  hasta := 17;
               end if;
               for nave in desde .. hasta loop
                  misBalas(bala).ValidoColision(misNaves(nave));
               end loop;
            end if;
         end if;
      end loop;

      -- Printeo pantalla
      for renglon in 1 .. 24 loop
         hayBala := False;
         for bala in misBalas'Range loop
            misBalas(bala).ObtenerEstado(estadoBala);
            misBalas(bala).ObtenerPos(posVer, posHor);
            if estadoBala = true and posVer = renglon then
               hayBala := True;
               posBala := posHor;
            end if;
         end loop;

         if renglon = 1 or renglon = 5 then -- Base de las naves enemigas, 3 bloques
            if renglon = 1 then
               desde := 1;
               hasta := 9;
            else
               desde := 10;
               hasta := 17;
            end if;
            posAnt := 1;
            for nave in desde .. hasta loop
               misNaves(nave).ObtenerEstado(estadoNave);
               if estadoNave = True then
                  misNaves(nave).ObtenerPos(posAux);
                  for columna in posAnt .. posAux - 1 loop
                     if hayBala = True and columna = posBala then
                        Put("^");
                     else
                        Put(" ");
                     end if;
                  end loop;
                  Put("***");
                  posAnt := posAux + 3;
               end if;
            end loop;
            for columna in posAnt .. 80 loop
               if hayBala = True and columna = posBala then
                  Put("^");
               else
                  Put(" ");
               end if;
            end loop;
         elsif renglon = 2 or renglon = 6 then -- Cañon de las naves enemigas, 1 bloque
            if renglon = 2 then
               desde := 1;
               hasta := 9;
            else
               desde := 10;
               hasta := 17;
            end if;
            posAnt := 1;
            for nave in desde .. hasta loop
               misNaves(nave).ObtenerEstado(estadoNave);
               if estadoNave = True then
                  misNaves(nave).ObtenerPos(posAux);
                  for columna in posAnt .. posAux loop
                     if hayBala = True and columna = posBala then
                        Put("^");
                     else
                        Put(" ");
                     end if;
                  end loop;
                  Put("*");
                  posAnt := posAux + 2;
               end if;
            end loop;
            for columna in posAnt .. 80 loop
               if hayBala = True and columna = posBala then
                  Put("^");
               else
                  Put(" ");
               end if;
            end loop;
         elsif renglon = 23 then -- Cañon del jugador, 1 bloque
            naveJugador.ObtenerPos(posAux);
            for columna in 1 .. posAux loop
               Put(" ");
            end loop;
            Put("*");
            for pos in posAux + 2 .. 80 loop
               Put(" ");
            end loop;
         elsif renglon = 24 then -- Base del jugador, 3 bloques
            naveJugador.ObtenerPos(posAux);
            for columna in 1 .. posAux -1 loop
               Put(" ");
            end loop;
            Put("***");
            for columna in posAux + 3 .. 80 loop
               Put(" ");
            end loop;
         else -- Renglones sin naves
            for columna in 1 .. 80 loop
               if hayBala = True and columna = posBala then
                  Put("^");
               else
                  Put(" ");
               end if;
            end loop;
         end if;
         Put_Line("");
      end loop;

      delay 0.2;
      Clear_Screen;
   end loop;

   -- Termino juego y tareas
   Put_Line("Felicidades has ganado.");
   for nave in misNaves'Range loop
      misNaves(nave).TerminarJuego;
   end loop;
   naveJugador.TerminarJuego;
   for bala in misBalas'Range loop
      misBalas(bala).TerminarJuego;
   end loop;
   abort Entrada; -- Google
end Main;
