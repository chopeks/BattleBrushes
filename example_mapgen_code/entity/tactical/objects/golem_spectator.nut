this.golem_spectator <- this.inherit("scripts/entity/tactical/entity", {
	m = {},
	function getName()
	{
		return "Flesh Golem Observer";
	}

	function getDescription()
	{
		return "A golem of flesh, watching you in stony silence";
	}

	function setFlipped( _flip )
	{
		this.getSprite("body").setHorizontalFlipping(_flip);
		this.getSprite("head").setHorizontalFlipping(_flip);
		this.getSprite("armor").setHorizontalFlipping(_flip);
		this.getSprite("helmet").setHorizontalFlipping(_flip);
	}

	function onInit()
	{
		local body = this.addSprite("body");
		body.setBrush("bust_flesh_golem_body_01");
		body.varyColor(0.05, 0.05, 0.05);
		body.varySaturation(0.1);
		local armor = this.addSprite("armor");
		armor.setBrush("bust_flesh_golem_armor_01");
		local head = this.addSprite("head");
		local golemHeads = [
			"bust_flesh_golem_head_01",
			"bust_flesh_golem_head_02",
			"bust_flesh_golem_head_03"
		];
		head.setBrush(golemHeads[this.Math.rand(0, golemHeads.len() - 1)]);
		head.Color = body.Color;
		head.Saturation = body.Saturation;
		local helmet = this.addSprite("helmet");

		if (this.Math.rand(1, 100) <= 80)
		{
			local facewraps = [
				"bust_flesh_golem_helmet_01",
				"bust_flesh_golem_helmet_02"
			];
			helmet.setBrush(facewraps[this.Math.rand(0, facewraps.len() - 1)]);
		}
	}

});

