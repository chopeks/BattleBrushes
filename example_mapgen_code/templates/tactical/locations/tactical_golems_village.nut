this.tactical_golems_village <- this.inherit("scripts/mapgen/tactical_template", {
	m = {},
	function init()
	{
		this.m.Name = "tactical.golems_village";
		this.m.MinX = 32;
		this.m.MinY = 32;
	}

	function fill( _rect, _properties, _pass = 1 )
	{
		for( local x = _rect.X; x < _rect.X + _rect.W; x = ++x )
		{
			for( local y = _rect.Y; y < _rect.Y + _rect.H; y = ++y )
			{
				local tile = this.Tactical.getTileSquare(x, y);
				local rearNorth = x >= 5 && x <= 10 && y >= 5 && y <= 10;
				local rearSouth = x >= 5 && x <= 10 && y >= _rect.H - 9 && y <= _rect.H - 4;
				local forwardMiddle = x >= 22 && x <= 27 && y >= 13 && y <= 18;
				local isSpawnZone = rearNorth || rearSouth || forwardMiddle;

				if (isSpawnZone || this.Math.rand(1, 100) <= 50)
				{
					tile.removeObject();
				}
				else if (this.Math.rand(1, 100) <= 10)
				{
					tile.clear();
					local r = this.Math.rand(1, 4);

					if (r == 1)
					{
						tile.spawnObject("entity/tactical/objects/graveyard_ruins");
					}
					else if (r == 2)
					{
						tile.spawnObject("entity/tactical/objects/graveyard_sarcophagus");
					}
					else
					{
						tile.spawnObject("entity/tactical/objects/graveyard_ruins_big");
					}
				}
				else if (this.Math.rand(1, 100) <= 20)
				{
					tile.clear();
					tile.spawnObject("entity/tactical/objects/graveyard_grave");
				}
				else if (this.Math.rand(1, 100) <= 30)
				{
					local deco = [
						"01",
						"02",
						"04",
						"05",
						"06",
						"07",
						"07",
						"13",
						"14",
						"15",
						"19",
						"28",
						"28"
					];
					tile.clear();
					tile.spawnDetail("graveyard_" + deco[this.Math.rand(0, deco.len() - 1)]);
				}
			}
		}
	}

});

