// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract HeartChain {
    struct Campaign {
        address creator;
        uint256 goal;
        uint256 raised;
        bool completed;
        string metadataCID;
    }

    mapping(uint256 => Campaign) public campaigns;
    uint256 public campaignCount;

    event CampaignCreated(uint256 indexed id, address indexed creator, uint256 goal, string metadataCID);
    event DonationReceived(uint256 indexed id, address indexed donor, uint256 amount);
    event CampaignCompleted(uint256 indexed id);

    function createCampaign(uint256 _goal, string calldata _metadataCID) external {
        require(_goal > 0, "Goal must be greater than 0");
        
        campaignCount++;
        campaigns[campaignCount] = Campaign({
            creator: msg.sender,
            goal: _goal,
            raised: 0,
            completed: false,
            metadataCID: _metadataCID
        });

        emit CampaignCreated(campaignCount, msg.sender, _goal, _metadataCID);
    }

    function donate(uint256 _id) external payable {
        require(_id > 0 && _id <= campaignCount, "Invalid campaign ID");
        Campaign storage campaign = campaigns[_id];
        require(!campaign.completed, "Campaign is closed");

        campaign.raised += msg.value;
        // In a real app, funds might be transferred to the creator here or held in escrow
        // For MVP, they stay in the contract or we transfer them:
        // payable(campaign.creator).transfer(msg.value);
        
        emit DonationReceived(_id, msg.sender, msg.value);
    }

    function completeCampaign(uint256 _id) external {
        Campaign storage campaign = campaigns[_id];
        require(msg.sender == campaign.creator, "Only creator can complete");
        campaign.completed = true;
        emit CampaignCompleted(_id);
    }
}
