<q:behavior name="PiranhaBehavior">
  <!-- Piranha Plant Behavior - Emerges and hides in pipes -->
  <q:set name="emergeHeight" value="32" type="integer" />
  <q:set name="hiddenY" value="0" type="float" />

  <qg:state-machine initial="hidden">
    <qg:state name="hidden">
      <qg:on event="emerge" transition="emerging" />
      <q:function name="enter">
        this.hiddenY = this.owner.sprite.y;
      </q:function>
    </qg:state>

    <qg:state name="emerging">
      <qg:on event="fullyOut" transition="visible" />
      <q:function name="update">
        this.owner.sprite.y -= 0.5;
        if (this.owner.sprite.y &lt;= this.hiddenY - this.emergeHeight) {
          this._smEmit('fullyOut');
        }
      </q:function>
    </qg:state>

    <qg:state name="visible">
      <qg:on event="hide" transition="hiding" />
    </qg:state>

    <qg:state name="hiding">
      <qg:on event="fullyHidden" transition="hidden" />
      <q:function name="update">
        this.owner.sprite.y += 0.5;
        if (this.owner.sprite.y >= this.hiddenY) {
          this._smEmit('fullyHidden');
        }
      </q:function>
    </qg:state>
  </qg:state-machine>
</q:behavior>
