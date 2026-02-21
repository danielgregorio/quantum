<q:prefab name="Coin">
  <!-- Spinning coin collectible -->
  <qg:sprite src="../assets/smw/sprites/objects.png"
             width="16" height="16"
             frame-x="0" frame-y="96"
             body="static" sensor="true" tag="coin">
    <qg:animation name="spin" frames="0-3" speed="0.1" loop="true" auto-play="true" />
  </qg:sprite>
</q:prefab>
