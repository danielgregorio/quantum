<q:prefab name="KoopaRed">
  <!-- Red Koopa - doesn't fall off edges -->
  <qg:sprite src="../assets/smw/sprites/koopas.png"
             width="16" height="24"
             frame-x="0" frame-y="0"
             body="dynamic" bounce="0" friction="0.3" tag="enemy">
    <qg:animation name="walk" frames="0-1" speed="0.15" loop="true" auto-play="true" />
    <qg:use behavior="PatrolBehavior" speed="0.8"
           on-collision="onWallHit" collision-tag="solid"
           on-collision="onEdgeDetected" collision-tag="edge" />
  </qg:sprite>
</q:prefab>
