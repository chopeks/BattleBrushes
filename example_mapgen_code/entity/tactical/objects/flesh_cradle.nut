this.flesh_cradle <- this.inherit("scripts/entity/tactical/entity", {
	m = {},
	function getName()
	{
		return "Flesh Cradle";
	}

	function getDescription()
	{
		return "A stone receptacle housing a variety of gore and viscera.";
	}

	function onInit()
	{
		local flip = false;
		local bottom = this.addSprite("bottom");
		bottom.setBrush("flesh_cradle_01_bottom");
		local top = this.addSprite("top");
		top.setBrush("flesh_cradle_01_top");
		this.setBlockSight(false);
	}

	function isDying()
	{
		return true;
	}

});

