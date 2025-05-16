terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_instance" "dl_training" {
  ami           = data.aws_ami.deep_learning_ami.id
  instance_type = "m5.xlarge"
  key_name      = aws_key_pair.training_key.key_name

  root_block_device {
    volume_size = 105
    volume_type = "gp3"
  }

  vpc_security_group_ids = [aws_security_group.training_sg.id]

  tags = {
    Name = "dl-training-instance"
  }
}


data "aws_ami" "deep_learning_ami" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["Deep Learning AMI (Amazon Linux 2) Version *"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_security_group" "training_sg" {
  name        = "training-sg"
  description = "Allow SSH and internet access for training"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "training-sg"
  }
}

resource "aws_key_pair" "training_key" {
  key_name   = "training-key"
  public_key = file("~/.ssh/id_rsa.pub")
}

output "instance_public_ip" {
  value = aws_instance.dl_training.public_ip
}