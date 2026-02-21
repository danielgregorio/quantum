<q:prefab name="KoopaGreen">
  <!-- Green Koopa - walks off edges -->
  <qg:sprite src="../assets/smw/sprites/koopas.png"
             width="16" height="24"
             frame-x="64" frame-y="0"
             body="dynamic" bounce="0" friction="0.3" tag="enemy">
    <qg:animation name="walk" frames="0-1" speed="0.15" loop="true" auto-play="true" />
    <qg:use behavior="PatrolBehavior" speed="1.0"
           on-collision="onWallHit" collision-tag="solid" />
  </qg:sprite>
</q:prefab>
