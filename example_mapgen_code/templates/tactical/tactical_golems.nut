this.tactical_golems <- this.inherit("scripts/mapgen/tactical_template", {
	m = {},
	function init()
	{
		this.m.Name = "tactical.golems";
		this.m.MinX = 28;
		this.m.MinY = 28;
	}

	function fill( _rect, _properties, _pass = 1 )
	{
		local stoneTile1 = this.MapGen.get("tactical.tile.stone1");
		stoneTile1.m.ChanceToSpawnObject = 7;
		local stoneTile2 = this.MapGen.get("tactical.tile.stone2");
		stoneTile2.m.ChanceToSpawnObject = 4;
		local earthTile1 = this.MapGen.get("tactical.tile.earth1");
		earthTile1.m.ChanceToSpawnAltDetails = 0;

		for( local x = _rect.X; x < _rect.X + _rect.W; x = ++x )
		{
			for( local y = _rect.Y; y < _rect.Y + _rect.H; y = ++y )
			{
				local tile = this.Tactical.getTileSquare(x, y);
				local isEntryTile = x <= _rect.X + 1 && y <= _rect.H / 2 + 1 && y >= _rect.H / 2 - 1 || x == _rect.X + 1 && y <= _rect.H / 2 + 1 && y >= _rect.H / 2 - 2;
				local isInner = x >= _rect.X + 4 && x <= _rect.W - 4 && y >= _rect.Y + 4 && y <= _rect.H - 4;

				if (!isEntryTile && (x <= _rect.X + 1 || y <= _rect.Y + 1 || x >= _rect.X + _rect.W - 2 || y >= _rect.Y + _rect.H - 2))
				{
					if (x <= _rect.X || y <= _rect.Y || x >= _rect.X + _rect.W - 1 || y >= _rect.Y + _rect.H - 1)
					{
						tile.Level = 3;
					}
					else
					{
						tile.Level = 2;
					}

					tile.Type = 0;

					if (this.Math.rand(1, 2) < 2)
					{
						stoneTile1.fill({
							X = x,
							Y = y,
							W = 1,
							H = 1,
							IsEmpty = true
						}, _properties, 1);
					}
					else
					{
						stoneTile2.fill({
							X = x,
							Y = y,
							W = 1,
							H = 1,
							IsEmpty = true
						}, _properties, 1);
					}
				}
				else
				{
					if (isInner && this.Math.rand(1, 100) <= 8)
					{
						tile.Level = 1;
					}
					else
					{
						tile.Level = 0;
					}

					if (tile.Type != 0)
					{
					}
					else
					{
						local r = this.Math.rand(1, 5);

						if (r == 1)
						{
							earthTile1.fill({
								X = x,
								Y = y,
								W = 1,
								H = 1,
								IsEmpty = true
							}, _properties, 1);
							earthTile1.fill({
								X = x,
								Y = y,
								W = 1,
								H = 1,
								IsEmpty = true
							}, _properties, 2);
						}

						if (r <= 3)
						{
							stoneTile1.fill({
								X = x,
								Y = y,
								W = 1,
								H = 1,
								IsEmpty = true
							}, _properties, 1);
							stoneTile1.fill({
								X = x,
								Y = y,
								W = 1,
								H = 1,
								IsEmpty = true
							}, _properties, 2);
						}
						else if (r <= 5)
						{
							stoneTile2.fill({
								X = x,
								Y = y,
								W = 1,
								H = 1,
								IsEmpty = true
							}, _properties, 1);
							stoneTile2.fill({
								X = x,
								Y = y,
								W = 1,
								H = 1,
								IsEmpty = true
							}, _properties, 2);
						}
					}
				}
			}
		}

		this.makeBordersImpassable(_rect);
	}

});

