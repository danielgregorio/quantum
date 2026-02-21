<q:prefab name="Rex">
  <!-- Rex - 2-hit enemy that squashes before dying -->
  <qg:sprite src="../assets/smw/sprites/rex_blargg_dino.png"
             width="16" height="32"
             frame-x="0" frame-y="0"
             body="dynamic" bounce="0" friction="0.3" tag="enemy">
    <qg:animation name="walk" frames="0-1" speed="0.2" loop="true" auto-play="true" />
    <qg:use behavior="RexBehavior" />
  </qg:sprite>
</q:prefab>
