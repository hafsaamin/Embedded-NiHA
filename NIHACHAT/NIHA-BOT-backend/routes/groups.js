const express = require('express');
const router = express.Router();
const Group = require('../models/Group');

// Create a new group
router.post('/', async (req, res) => {
  const { name, username } = req.body;
  const newGroup = new Group({ name, username });
  try {
    await newGroup.save();
    res.status(201).json(newGroup);
  } catch (error) {
    res.status(500).json({ error: 'Failed to create group' });
  }
});

// Get all groups for a user
router.get('/:username', async (req, res) => {
  try {
    const groups = await Group.find({ username: req.params.username });
    res.json(groups);
  } catch (error) {
    res.status(500).json({ error: 'Failed to retrieve groups' });
  }
});

// Add conversation to group
router.post('/:groupId/conversations', async (req, res) => {
  const { conversationId } = req.body;
  try {
    await Group.findByIdAndUpdate(req.params.groupId, {
      $addToSet: { conversations: conversationId }
    });
    res.status(200).json({ message: 'Conversation added to group' });
  } catch (error) {
    res.status(500).json({ error: 'Failed to add conversation to group' });
  }
});

module.exports = router;
