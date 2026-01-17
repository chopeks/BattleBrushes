this.tactical_golems_lair <- this.inherit("scripts/mapgen/tactical_template", {
	m = {
		Details = [
			"blood_red_01",
			"blood_red_02",
			"blood_red_03",
			"blood_red_04",
			"blood_red_05",
			"blood_red_06",
			"blood_red_07",
			"blood_red_08",
			"blood_red_09",
			"blood_red_10",
			"blood_red_01",
			"blood_red_02",
			"blood_red_03",
			"blood_red_04",
			"blood_red_05",
			"blood_red_06",
			"blood_red_07",
			"blood_red_08",
			"blood_red_09",
			"blood_red_10",
			"corpse_part_01",
			"corpse_part_02",
			"corpse_part_03",
			"corpse_part_04",
			"corpse_part_05"
		]
	},
	function init()
	{
		this.m.Name = "tactical.golems_lair";
		this.m.MinX = 28;
		this.m.MinY = 28;
	}

	function fill( _rect, _properties, _pass = 1 )
	{
		local cradlesSpawned = 0;
		local lastCradleX = 0;
		local lastCradleY = 0;

		for( local x = _rect.X; x < _rect.X + _rect.W; x = ++x )
		{
			for( local y = _rect.Y; y < _rect.Y + _rect.H; y = ++y )
			{
				local tile = this.Tactical.getTileSquare(x, y);
				local isEntryTile = x <= _rect.X + 1 && y <= _rect.H / 2 + 1 && y >= _rect.H / 2 - 1 || x == _rect.X + 1 && y <= _rect.H / 2 + 1 && y >= _rect.H / 2 - 2;

				if (this.Math.rand(1, 100) <= 50)
				{
					tile.removeObject();
				}

				if (isEntryTile)
				{
					tile.spawnObject("entity/tactical/objects/autumn_boulder1");
				}
				else if (x > _rect.X + 1 && x < _rect.X + _rect.W - 2 && y > _rect.Y + 1 && y < _rect.Y + _rect.H - 2)
				{
					if (this.Math.rand(1, 100) <= 3)
					{
						tile.clear();
						tile.spawnDetail(this.m.Details[this.Math.rand(0, this.m.Details.len() - 1)]);
					}
				}
				else if (this.Math.rand(1, 100) <= 66)
				{
					local o = tile.spawnObject("entity/tactical/objects/golem_spectator");

					if (o != null)
					{
						if (tile.Coords.X > (_rect.X + _rect.W) / 2)
						{
							o.setFlipped(false);
						}
						else
						{
							o.setFlipped(true);
						}
					}
				}
			}
		}
	}

});

