this.flesh_cradle_destroyed <- this.inherit("scripts/entity/tactical/entity", {
	m = {},
	function getName()
	{
		return "Destroyed Flesh Cradle";
	}

	function getDescription()
	{
		return "A destroyed stone receptacle. The guts and gore once housed within have slopped onto the surrounding ground.";
	}

	function onInit()
	{
		local flip = false;
		local body = this.addSprite("body");
		body.setBrush("flesh_cradle_01_destroyed");
		this.setBlockSight(false);
	}

	function isDying()
	{
		return true;
	}

});

