<q:prefab name="QuestionBlock">
  <!-- Question Block - hit from below to get coins/powerups -->
  <qg:sprite src="../assets/smw/sprites/objects.png"
             width="16" height="16"
             frame-x="0" frame-y="0"
             body="static" tag="qblock">
    <qg:animation name="shine" frames="0-3" speed="0.2" loop="true" auto-play="true" />
    <qg:use behavior="QuestionBlockBehavior" contents="coin" />
  </qg:sprite>
</q:prefab>
